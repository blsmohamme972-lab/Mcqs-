"""Voice examiner: an oral exam (viva) over the book's Q&A cards, then FSRS spaced repetition from the result.

The owner starts a voice call with ChatGPT or Claude using the examiner prompt of a session, answers aloud, and at the
end the examiner writes a short JSON report (one row per question: result, key points hit, hints, fluency, confidence,
retry). `mark` turns every row into an FSRS rating and reschedules the card. Same FSRS-6 engine as the app
(py-fsrs 6.3.2, which `android/.../srs/Fsrs.kt` is verified against), without learning steps: a voice session is a
day-scale event, so every answer schedules in days.

Files (text only, committed): examiner/bank/chNN.json (cards), examiner/state.json (schedule + history),
examiner/sessions/<sid>.plan.json / <sid>.report.json (what was asked, what happened).
"""
from __future__ import annotations
import json, re, subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fsrs import Card, Rating, Scheduler

BOOK = "Cardiothoracic Surgery, 2nd edition"
TYPES = ("recall", "list", "why", "case", "compare", "value")
RESULTS = ("correct", "partial", "wrong", "blank")
FLUENCY = ("fluent", "hesitant", "guessed")
CONFIDENCE = ("sure", "unsure")
CARD_ID_RE = re.compile(r"ch(\d\d)\.p(\d{3,4})\.(\d\d)")
SID_RE = re.compile(r"S\d{8}-\d{4}")
MIN_PER_CARD = 1.2          # question + answer + feedback, aloud
DUE_AHEAD = timedelta(hours=6)  # a card due later today is still asked now
LEECH_LAPSES = 4            # this many failures after learning it: teach it instead of quizzing it
NUDGE_TO = timedelta(days=1)    # a failed card pulls its page siblings forward to tomorrow
NUDGE_IF_LATER = timedelta(days=2)
RETRY_GAP = timedelta(minutes=10)
MAX_NOTES = 5

# Importance: every card is rated when it is written, on five criteria (0-3 each), the way certifying boards weigh
# the content of an exam (practice analysis / blueprinting: how critical, how frequent, how often examined), plus
# how much management turns on it and how much else is built on it. The tool, not the writer, turns them into a score.
CRITERIA = {  # weight, and what 0..3 means
    "safety": (0.30, "harm if the surgeon does not know it: 0 none, 1 minor, 2 a complication or the wrong operation, "
                     "3 death or catastrophe (emergency, red flag, absolute contraindication)"),
    "decision": (0.25, "how much it changes what you do: 0 background or history, 1 informs, 2 changes the test, timing "
                       "or technique, 3 decides whether or what to operate (indication, contraindication, threshold)"),
    "frequency": (0.20, "how often a cardiothoracic surgeon meets it: 0 a rarity, 1 occasionally, 2 every week, "
                        "3 every day or every patient"),
    "exam": (0.15, "how often board examiners ask it (FRCS-CTh, EBCTS, ABTS viva style): 0 never, 1 sometimes, 2 often, "
                   "3 a classic (classification, guideline indications, named scores, key numbers)"),
    "core": (0.10, "how much else is built on it: 0 stands alone, 1 a little, 2 many topics, 3 a foundation "
                   "(anatomy or physiology the rest depends on)"),
}
TIERS = {"A": "must know", "B": "should know", "C": "nice to know"}
TIER_A, TIER_B = 65, 40
RETENTION = {"A": 0.95, "B": 0.90, "C": 0.85}  # the more it matters, the less forgetting we accept
SCHEDULERS = {t: Scheduler(learning_steps=(), relearning_steps=(), desired_retention=r, enable_fuzzing=True)
              for t, r in RETENTION.items()}
SCHEDULER = SCHEDULERS["B"]


def importance_score(imp: dict) -> int:
    """0-100 from the five criteria."""
    return round(100 * sum(w * imp[k] / 3 for k, (w, _) in CRITERIA.items()))


def tier(card: dict) -> str:
    """A: score 65+ or anything that can kill (a critical item is must-know whatever else); B: 40+; C: the rest."""
    imp = card["importance"]
    sc = importance_score(imp)
    return "A" if sc >= TIER_A or imp["safety"] == 3 else "B" if sc >= TIER_B else "C"


def weight(card: dict) -> float:
    """How much a card's forgetting counts when there is more due than time: 0.5 (score 0) to 1.5 (score 100)."""
    return 0.5 + importance_score(card["importance"]) / 100


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


# ---------- bank ----------

def check_card(c: dict) -> None:
    """A card is one oral question with a model answer and the key points that must be said for full marks."""
    m = CARD_ID_RE.fullmatch(c.get("id", ""))
    if not m: raise ValueError(f"bad id {c.get('id')!r} (want chNN.pPPP.NN)")
    extra = set(c) - {"id", "chapter", "page", "topic", "type", "q", "a", "points", "importance", "related", "tags"}
    if extra: raise ValueError(f"{c['id']}: unknown fields {sorted(extra)}")
    if c.get("chapter") != int(m[1]) or c.get("page") != int(m[2]): raise ValueError(f"{c['id']}: chapter/page do not match the id")
    if c.get("type") not in TYPES: raise ValueError(f"{c['id']}: type must be one of {TYPES}")
    for k in ("q", "a"):
        if not isinstance(c.get(k), str) or not c[k].strip(): raise ValueError(f"{c['id']}: empty {k}")
    if len(c["q"]) > 300 or len(c["a"]) > 500: raise ValueError(f"{c['id']}: question or answer too long to say aloud")
    pts = c.get("points")
    if not (isinstance(pts, list) and 1 <= len(pts) <= 5 and all(isinstance(p, str) and p.strip() for p in pts)):
        raise ValueError(f"{c['id']}: points must be 1-5 short strings")
    if not all(CARD_ID_RE.fullmatch(r) for r in c.get("related", [])): raise ValueError(f"{c['id']}: bad related id")
    imp = c.get("importance")
    if not isinstance(imp, dict) or set(imp) != {*CRITERIA, "why"}:
        raise ValueError(f"{c['id']}: importance needs {sorted(CRITERIA)} and why")
    if not all(imp[k] in (0, 1, 2, 3) for k in CRITERIA): raise ValueError(f"{c['id']}: importance criteria are 0-3")
    if not isinstance(imp["why"], str) or not imp["why"].strip(): raise ValueError(f"{c['id']}: importance.why is empty")


def calibration(cards: list[dict]) -> dict:
    """Tier shares of a set of cards, with a warning when ratings look inflated (a writer rating page by page tends to
    call everything important; across the specialty only about a quarter of facts are must-know)."""
    n = len(cards) or 1
    share = {t: sum(tier(c) == t for c in cards) / n for t in TIERS}
    warn = []
    if share["A"] > 0.40: warn.append(f"{share['A']:.0%} of cards are tier A (expected about 20-35%): rate against the whole specialty")
    if len(cards) >= 10 and share["C"] == 0: warn.append("no tier C card: background facts should be rated low")
    return {"cards": len(cards), "share": share, "warnings": warn}


def load_bank(bank_dir: Path) -> dict[str, dict]:
    cards = {}
    for f in sorted(bank_dir.glob("ch*.json")):
        for c in json.loads(f.read_text(encoding="utf-8"))["cards"]:
            check_card(c)
            if c["id"] in cards: raise ValueError(f"duplicate card id {c['id']}")
            cards[c["id"]] = c
    return cards


def merge_cards(bank_file: Path, chapter: int, title: str, new: list[dict]) -> tuple[int, int]:
    """Add or replace cards (by id) in one chapter's bank file; returns (added, replaced)."""
    data = json.loads(bank_file.read_text(encoding="utf-8")) if bank_file.exists() else {"chapter": chapter, "title": title, "cards": []}
    have = {c["id"]: i for i, c in enumerate(data["cards"])}
    added = replaced = 0
    for c in new:
        check_card(c)
        if c["chapter"] != chapter: raise ValueError(f"{c['id']} is not chapter {chapter}")
        if c["id"] in have: data["cards"][have[c["id"]]] = c; replaced += 1
        else: have[c["id"]] = len(data["cards"]); data["cards"].append(c); added += 1
    data["cards"].sort(key=lambda c: c["id"])
    bank_file.parent.mkdir(parents=True, exist_ok=True)
    bank_file.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return added, replaced


# ---------- pages -> Q&A (the prompt only; the cards are written by Claude or ChatGPT and added with merge_cards) ----------

def book_page(text: str) -> int | None:
    """Printed page number from a page's running head: '2    CHAPTER 1 ...' or '... HISTORY      3'."""
    head = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    m = re.match(r"(\d{1,4})\s", head) or re.search(r"\s(\d{1,4})$", head)
    return int(m[1]) if m else None


def page_texts(pdf: Path) -> list[dict]:
    raw = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], check=True, capture_output=True, text=True).stdout
    pages = []
    for i, t in enumerate(raw.split("\f"), 1):
        if t.strip(): pages.append({"pdf_page": i, "page": book_page(t), "text": t.rstrip()})
    return pages


QA_RULES = """\
You turn pages of the book into oral exam cards (a viva), for one student who will be examined by voice.
Use ONLY what these pages say: no outside facts, numbers, doses or drug names that are not on the page.

Each card is one question an examiner asks aloud and the student answers aloud in under 30 seconds.
- q: one spoken question. No multiple choice, no "which of the following", no symbols (write "more than", not ">").
  Mix the types: recall (what is), list (name the...), why (mechanism / reason), case (a two-line patient -> what do
  you do / what is it), compare (X versus Y), value (a number or threshold the page gives).
- a: the model answer in 1-3 sentences, in the page's own facts.
- points: 1-5 short key points the student must say for full marks (the names, numbers and thresholds, as the page
  words them). The examiner marks the answer by counting these.
- page: the printed book page the fact is on. id: chNN.pPPP.NN (chapter, printed page, 01, 02 ... in page order).
- related: ids of cards on the same idea (so a failure on one brings the others forward). topic: the page's heading.
- About one card per examinable fact group: usually 4-8 per page; none for a page with no teachable content.
- Prefer what a cardiothoracic examiner really asks: indications, classifications, red flags, steps, numbers.

IMPORTANCE (rate every card; the study order is built from it, not from the page order)
Score each criterion 0-3 for a cardiothoracic surgeon and a board examiner, judged against the WHOLE specialty, not
this page. The tool computes the score and the tier (A must know, B should know, C nice to know) from them.
{criteria}
- why: one line giving the reason (e.g. "missed tamponade kills; a classic viva question").
- Be strict: across the book only about a quarter of cards are tier A. History-taking details, background and
  rarities are rated low even when the page spends many words on them; a short line that can save a life is rated high.

Reply with ONLY one JSON object: {{"cards": [{{"id", "chapter", "page", "topic", "type", "q", "a", "points",
"importance": {{"safety", "decision", "frequency", "exam", "core", "why"}}, "related"}}, ...]}}
"""


def qa_prompt(chapter: int, title: str, pages: list[dict]) -> str:
    body = "\n\n".join(f"=== book page {p['page'] or '?'} (pdf page {p['pdf_page']}) ===\n{p['text']}" for p in pages)
    crit = "\n".join(f"- {k} (weight {w:.0%}): {d}" for k, (w, d) in CRITERIA.items())
    return f"{QA_RULES.format(criteria=crit)}\nBook: {BOOK}. Chapter {chapter}: {title}.\n\n{body}\n"


# ---------- state ----------

def load_state(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"schema": 1, "cards": {}, "sessions": []}


def save_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def fsrs_card(entry: dict) -> Card:
    return Card.from_dict(entry["fsrs"])


def scheduler_for(card: dict) -> Scheduler:
    return SCHEDULERS[tier(card)]


def retrievability(entry: dict, now: datetime) -> float:
    return SCHEDULER.get_card_retrievability(fsrs_card(entry), current_datetime=now)


# ---------- session plan ----------

def interleave(ids: list[str], bank: dict) -> list[str]:
    """Keep the priority order, but never ask two cards from the same page back to back when it can be avoided."""
    left, out = list(ids), []
    while left:
        prev = bank[out[-1]]["page"] if out else None
        i = next((k for k, x in enumerate(left) if bank[x]["page"] != prev), 0)
        out.append(left.pop(i))
    return out


def plan_session(bank: dict, state: dict, now: datetime, minutes: int = 20, new: int = 8,
                 chapters: list[int] | None = None, sid: str | None = None, tiers: list[str] | None = None) -> dict:
    """Pick what to ask: confident errors first, then due cards (the most important forgetting first), new cards by
    importance (the scope can be one chapter or the whole book; `tiers` limits the NEW cards, e.g. only A), and up to
    two leeches to teach. Fits about `minutes` of talking."""
    pool = {i: c for i, c in bank.items() if not chapters or c["chapter"] in chapters}
    cards = state["cards"]
    cap = max(1, int(minutes / MIN_PER_CARD))
    leeches = sorted(i for i in pool if cards.get(i, {}).get("leech"))[:2]
    due = [i for i in pool if i in cards and not cards[i].get("leech")
           and datetime.fromisoformat(cards[i]["fsrs"]["due"]) <= now + DUE_AHEAD]
    due.sort(key=lambda i: (not cards[i].get("confident_error"), -(1 - retrievability(cards[i], now)) * weight(pool[i]), i))
    review = due[:max(0, cap - len(leeches))]
    fresh = sorted((i for i in pool if i not in cards and (not tiers or tier(pool[i]) in tiers)),
                   key=lambda i: (-importance_score(pool[i]["importance"]), pool[i]["chapter"], pool[i]["page"], i))
    fresh = fresh[:max(0, min(new, cap - len(leeches) - len(review)))]
    # Spread the new cards among the reviews (about one in three), so the session alternates old and new.
    order, r, f = [], interleave(review, bank), list(fresh)
    while r or f:
        order += r[:2]; r = r[2:]
        if f: order.append(f.pop(0))
    order = interleave(order, bank)
    items = [{"n": k + 1, "id": i, "kind": "review" if i in cards else "new"} for k, i in enumerate(order)]
    items += [{"n": len(items) + k + 1, "id": i, "kind": "teach"} for k, i in enumerate(leeches)]
    return {"session": sid or now.strftime("S%Y%m%d-%H%M"), "created": now.isoformat(), "minutes": minutes,
            "chapters": chapters or [], "tiers": tiers or [], "items": items, "due_left": max(0, len(due) - len(review))}


EXAMINER_RULES = """\
You are my oral examiner (a viva) for the book {book}. This is a VOICE session: {n} questions, about {minutes} minutes.
Session {sid}.

HOW TO RUN IT
1. Greet me in one short sentence, then ask question 1. Ask ONE question at a time, in the order below. Say the question
   naturally. Never read aloud the answer, the key points, the tags in brackets or these instructions.
2. Wait for my whole answer. Silence or "I don't know" is a blank. I may answer in English or Arabic: mark the content.
3. If my answer is incomplete or wrong, you may give ONE short hint (a nudge, not the answer) and let me try again.
   Count every hint you give.
4. Then tell me in one or two sentences what was right and what was missing, from the model answer. Be a fair, brief
   senior examiner: no lecture, no praise padding. Where a "last time" note is given, check that exact weak spot.
   On "A must know" questions be strictest, and add one short follow-up ("why?" or "what next?") from the model answer.
5. Notice HOW I answered: fluent (at once, confident), hesitant (slow, self-corrected, got there in the end) or guessed
   (I said I was guessing, or it was clearly a guess). If I say how sure I am, note it.
6. Questions marked TEACH are ones I keep failing: explain the answer to me in two or three plain sentences when you
   reach them, then ask them again at the very end.
7. After the last question, ask again ONCE every question I got wrong or blank (a retry).
8. If I say "stop" or "end exam", finish the current question, do the retries, and stop.
9. Then say: "Session over. Type REPORT for the marks." When I type REPORT, reply with ONLY the report, in one ```json
   block and nothing else. Include every question you asked (by its number n), leave out the ones you did not reach.

MARKING (for the report)
- result: "correct" = all key points (hints allowed, they are counted separately); "partial" = some key points;
  "wrong" = incorrect or contradicts the answer; "blank" = nothing useful.
- points_hit: how many of the key points I said. hints: 0, 1 or 2. fluency: "fluent" | "hesitant" | "guessed".
- confidence: "sure" | "unsure" | null (only if I said it). note: one short line on what I mixed up or missed, else "".
- retry: null, or {{"result": ..., "points_hit": ..., "hints": ...}} for a question you asked again.

REPORT FORMAT
{{"session": "{sid}", "items": [
  {{"n": 1, "result": "partial", "points_hit": 1, "hints": 1, "fluency": "hesitant", "confidence": null,
    "note": "forgot class IV", "retry": null}}
]}}

QUESTIONS
"""


def examiner_prompt(plan: dict, bank: dict, state: dict) -> str:
    out = [EXAMINER_RULES.format(book=BOOK, n=len(plan["items"]), minutes=plan["minutes"], sid=plan["session"])]
    for it in plan["items"]:
        c, entry = bank[it["id"]], state["cards"].get(it["id"], {})
        t = tier(c)
        tag = [it["kind"].upper() if it["kind"] == "teach" else it["kind"], f"{t} {TIERS[t]}", f"Ch{c['chapter']} p{c['page']}"]
        if entry.get("notes"): tag.append("last time: " + entry["notes"][-1]["note"])
        pts = "\n".join(f"     - {p}" for p in c["points"])
        out.append(f"{it['n']}. [{' · '.join(tag)}]\n   Q: {c['q']}\n   Model answer: {c['a']}\n"
                   f"   Key points ({len(c['points'])}):\n{pts}\n")
    return "\n".join(out)


# ---------- report -> ratings ----------

def parse_report(text: str) -> dict:
    """The report as pasted: a bare JSON object, or one inside a ```json block with chat around it."""
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    raw = m[1] if m else text[text.find("{"): text.rfind("}") + 1]
    rep = json.loads(raw)
    if not isinstance(rep.get("items"), list): raise ValueError("report has no items list")
    for it in rep["items"]:
        if it.get("result") not in RESULTS: raise ValueError(f"item {it.get('n')}: result must be one of {RESULTS}")
        if it.get("fluency", "fluent") not in FLUENCY: raise ValueError(f"item {it.get('n')}: bad fluency")
        if it.get("confidence") not in (None, *CONFIDENCE): raise ValueError(f"item {it.get('n')}: bad confidence")
        if it.get("retry") is not None and it["retry"].get("result") not in RESULTS: raise ValueError(f"item {it['n']}: bad retry")
    return rep


def rate(item: dict, n_points: int, lapses: int = 0) -> tuple[Rating, str]:
    """One spoken answer -> FSRS rating, with the reason in words.

    Again: wrong, blank, less than half the key points, or right only after two hints.
    Hard:  partial (half or more), one hint, or a correct guess.
    Good:  correct but hesitant, unsure or not every key point; a once-failed card never gets more than Good.
    Easy:  every key point, at once, no hint, not unsure.
    """
    if item.get("override") in (1, 2, 3, 4): return Rating(item["override"]), "set by the owner"
    res, hints = item["result"], int(item.get("hints") or 0)
    if res in ("wrong", "blank"): return Rating.Again, res
    hit = item.get("points_hit")
    cov = 1.0 if hit is None and res == "correct" else min(1.0, (hit or 0) / max(1, n_points))
    if res == "partial":
        return (Rating.Hard, f"partial, {hit}/{n_points} points") if cov >= 0.5 and hints < 2 else (Rating.Again, f"partial, {hit}/{n_points} points")
    if hints >= 2: return Rating.Again, "correct only after two hints"
    if hints == 1: return Rating.Hard, "correct after a hint"
    if item.get("fluency") == "guessed": return Rating.Hard, "correct guess"
    if item.get("fluency") == "hesitant" or item.get("confidence") == "unsure" or cov < 1: return Rating.Good, "correct, not fluent or not complete"
    if lapses > 0: return Rating.Good, "correct and fluent (failed before, so not Easy)"
    return Rating.Easy, "correct, fluent, complete"


def _review(entry: dict | None, rating: Rating, when: datetime, sch: Scheduler = SCHEDULER) -> dict:
    card = fsrs_card(entry) if entry else Card(card_id=1, due=when)
    was_learned = entry is not None and entry["fsrs"].get("last_review") is not None
    card, _ = sch.review_card(card, rating, review_datetime=when)
    e = dict(entry or {"reps": 0, "lapses": 0, "history": [], "notes": []})
    e["fsrs"] = card.to_dict()
    e["reps"] += 1
    if rating == Rating.Again and was_learned: e["lapses"] += 1
    return e


def mark(plan: dict, report: dict, state: dict, bank: dict, now: datetime) -> list[dict]:
    """Apply a session's report to the state (in place). Returns one row per card for the summary."""
    sid = plan["session"]
    if report.get("session") not in (None, sid): raise ValueError(f"report is for {report['session']}, plan is {sid}")
    if sid in state["sessions"]: raise ValueError(f"{sid} is already marked")
    by_n = {it["n"]: it for it in plan["items"]}
    first, second = now - RETRY_GAP, now
    rows, failed = [], []
    for it in report["items"]:
        p = by_n.get(it["n"])
        if not p: raise ValueError(f"report item n={it['n']} is not in the plan")
        cid, c = p["id"], bank[p["id"]]
        entry = state["cards"].get(cid)
        rating, why = rate(it, len(c["points"]), entry["lapses"] if entry else 0)
        if p["kind"] == "teach" and rating == Rating.Easy: rating, why = Rating.Good, why + " (taught today)"
        sch = scheduler_for(c)
        e = _review(entry, rating, first, sch)
        e["history"].append({"t": first.isoformat(), "s": sid, "r": int(rating), "why": why})
        if it.get("note"):
            e["notes"] = (e["notes"] + [{"t": first.date().isoformat(), "note": it["note"]}])[-MAX_NOTES:]
        e["confident_error"] = rating == Rating.Again and it.get("confidence") == "sure"
        retry = it.get("retry")
        if retry:
            r2, why2 = rate({**retry, "fluency": retry.get("fluency", "hesitant")}, len(c["points"]), e["lapses"])
            r2 = min(r2, Rating.Good, key=int)  # a same-call retry shows short-term memory, not learning
            e = _review(e, r2, second, sch)
            e["history"].append({"t": second.isoformat(), "s": sid, "r": int(r2), "why": "retry: " + why2})
        if e["lapses"] >= LEECH_LAPSES and rating == Rating.Again: e["leech"] = True
        if p["kind"] == "teach" and rating >= Rating.Good: e["leech"] = False
        state["cards"][cid] = e
        if rating == Rating.Again: failed.append(cid)
        rows.append({"n": it["n"], "id": cid, "rating": rating.name, "why": why, "due": e["fsrs"]["due"],
                     "retry": e["history"][-1]["why"] if retry else None, "leech": bool(e.get("leech"))})
    rows += nudge_related(failed, state, bank, now)
    state["sessions"].append(sid)
    return rows


def nudge_related(failed: list[str], state: dict, bank: dict, now: datetime) -> list[dict]:
    """A failed card is a sign the whole idea is fading: bring its page siblings and related cards forward to tomorrow
    (the schedule moves, the memory model does not)."""
    rows = []
    for cid in failed:
        c = bank[cid]
        sib = {i for i, x in bank.items() if x["chapter"] == c["chapter"] and x["page"] == c["page"]}
        sib |= set(c.get("related", [])) | {i for i, x in bank.items() if cid in x.get("related", [])}
        for i in sorted(sib - {cid} - set(failed)):
            e = state["cards"].get(i)
            if not e: continue
            due = datetime.fromisoformat(e["fsrs"]["due"])
            if due > now + NUDGE_IF_LATER:
                e["fsrs"]["due"] = (now + NUDGE_TO).isoformat()
                e["history"].append({"t": now.isoformat(), "s": "nudge", "r": 0, "why": f"{cid} failed"})
                rows.append({"n": None, "id": i, "rating": "moved", "why": f"related to {cid}, which failed", "due": e["fsrs"]["due"]})
    return rows


# ---------- status ----------

def status(bank: dict, state: dict, now: datetime) -> dict:
    cards = state["cards"]
    due_at = {i: datetime.fromisoformat(e["fsrs"]["due"]) for i, e in cards.items() if i in bank}
    by_ch: dict[int, dict] = {}
    for i, c in bank.items():
        s = by_ch.setdefault(c["chapter"], {"cards": 0, "new": 0, "due": 0, "leech": 0, "A": 0, "B": 0, "C": 0, "new_A": 0})
        s["cards"] += 1; s[tier(c)] += 1
        if i not in cards and tier(c) == "A": s["new_A"] += 1
        if i not in cards: s["new"] += 1
        elif due_at[i] <= now + DUE_AHEAD: s["due"] += 1
        if cards.get(i, {}).get("leech"): s["leech"] += 1
    weak = sorted((i for i in cards if i in bank),
                  key=lambda i: (-(1 - retrievability(cards[i], now)) * weight(bank[i]), -cards[i]["lapses"]))[:5]
    return {"chapters": by_ch, "due_now": sum(s["due"] for s in by_ch.values()),
            "due_week": sum(1 for d in due_at.values() if d <= now + timedelta(days=7)),
            "weakest": [{"id": i, "q": bank[i]["q"], "tier": tier(bank[i]), "recall": round(retrievability(cards[i], now), 2),
                         "lapses": cards[i]["lapses"]} for i in weak],
            "sessions": len(state["sessions"])}
