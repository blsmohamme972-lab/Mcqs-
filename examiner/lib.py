"""Voice examiner: a board-style oral exam (viva) over the whole book, then FSRS spaced repetition from the result.

The viva follows the UK Intercollegiate FRCS Section 2 oral (the board exam of the specialty): topics of 5 minutes,
two examiners taking three topics each, short questions climbing a ladder (knowledge, understanding, management,
complications and evidence), every topic marked 4 to 8 with 6 the pass mark, and a topic sheet so a topic is not
asked twice on the same day. The owner runs it as a voice call with ChatGPT or Claude from the session's examiner
prompt; at the end the examiner writes a short JSON report (one mark per topic, one row per question). `mark` keeps
the viva marks and turns every question into an FSRS rating. Same FSRS-6 engine as the app (py-fsrs 6.3.2, which
`android/.../srs/Fsrs.kt` is verified against), without learning steps: a viva is a day-scale event.

Nothing in the book is lost: every page is broken into its facts (or skipped with a reason), and every fact is
tested by at least one card (`coverage`). Importance decides the ORDER, never what is left out.

Files (text only, committed): examiner/bank/chNN.json (page facts + cards), examiner/state.json (schedule, viva
marks, history), examiner/sessions/<sid>.plan.json / <sid>.report.json (what was asked, what happened).
"""
from __future__ import annotations
import json, re, subprocess
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fsrs import Card, Rating, Scheduler

BOOK = "Cardiothoracic Surgery, 2nd edition"
TYPES = ("recall", "list", "why", "case", "compare", "value")
LEVELS = {1: "knowledge", 2: "understanding", 3: "management", 4: "complications and evidence"}  # the viva ladder
RESULTS = ("correct", "partial", "wrong", "blank")
FLUENCY = ("fluent", "hesitant", "guessed")
CONFIDENCE = ("sure", "unsure")
CARD_ID_RE = re.compile(r"ch(\d\d)\.p(\d{3,4})\.(\d\d)")
FACT_ID_RE = re.compile(r"p(\d{3,4})\.f(\d\d)")
Q_MAX, A_MAX = 160, 200     # short: a question said in one breath, an answer in a few seconds
DUE_AHEAD = timedelta(hours=6)  # a card due later today is still asked now
LEECH_LAPSES = 4            # this many failures after learning it: teach it instead of quizzing it
NUDGE_TO = timedelta(days=1)    # a failed card pulls its page siblings forward to tomorrow
NUDGE_IF_LATER = timedelta(days=2)
RETRY_GAP = timedelta(minutes=10)
MAX_NOTES = 5

# The viva (board format): 5-minute topics, about five short questions each, two examiners; a full viva is 6 topics.
TOPIC_MIN, Q_PER_TOPIC, FULL_VIVA = 5, 5, 6
VIVAS = {  # the four vivas of the exam, by the book's chapters
    "critical": ("Critical care, basic science and perioperative care", (1, 2, 3, 4, 5, 6)),
    "cardiac": ("Adult cardiac surgery", (7, 8, 9, 10, 11)),
    "congenital": ("Congenital cardiac surgery", (12,)),
    "thoracic": ("Thoracic surgery", (13, 14, 15, 16, 17)),
}
MARKS = {  # one mark per topic, as in the board viva; 6 is the pass mark
    8: "very good pass: complete, structured and fluent, safe throughout, reaches the top of the ladder with little or no prompting",
    7: "good pass: safe and well organised, minor gaps only, few prompts",
    6: "pass: safe, gives the essentials of the topic, needs some prompting, does not get far up the ladder",
    5: "fail: gaps in the essentials or needs leading, but nothing dangerous",
    4: "bad fail: a dangerous answer, or cannot give the essentials even with prompting",
}
PASS_MARK = 6

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


def viva_of(chapter: int) -> str:
    return next(k for k, (_, chs) in VIVAS.items() if chapter in chs)


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


# ---------- bank: page facts + cards ----------

def check_card(c: dict) -> None:
    """A card is one short oral question with a model answer, the key points that must be said, its rung on the viva
    ladder, the page facts it tests, and its importance."""
    m = CARD_ID_RE.fullmatch(c.get("id", ""))
    if not m: raise ValueError(f"bad id {c.get('id')!r} (want chNN.pPPP.NN)")
    extra = set(c) - {"id", "chapter", "page", "topic", "type", "level", "q", "a", "points", "facts", "importance", "related", "tags"}
    if extra: raise ValueError(f"{c['id']}: unknown fields {sorted(extra)}")
    if c.get("chapter") != int(m[1]) or c.get("page") != int(m[2]): raise ValueError(f"{c['id']}: chapter/page do not match the id")
    if c.get("type") not in TYPES: raise ValueError(f"{c['id']}: type must be one of {TYPES}")
    if c.get("level") not in LEVELS: raise ValueError(f"{c['id']}: level must be 1-4 ({', '.join(LEVELS.values())})")
    for k in ("q", "a", "topic"):
        if not isinstance(c.get(k), str) or not c[k].strip(): raise ValueError(f"{c['id']}: empty {k}")
    if len(c["q"]) > Q_MAX or len(c["a"]) > A_MAX:
        raise ValueError(f"{c['id']}: keep it short (question up to {Q_MAX} characters, answer up to {A_MAX})")
    pts = c.get("points")
    if not (isinstance(pts, list) and 1 <= len(pts) <= 4 and all(isinstance(p, str) and p.strip() for p in pts)):
        raise ValueError(f"{c['id']}: points must be 1-4 short strings")
    if not (isinstance(c.get("facts"), list) and c["facts"] and all(FACT_ID_RE.fullmatch(f) for f in c["facts"])):
        raise ValueError(f"{c['id']}: facts must list the page facts it tests (pPPP.fNN)")
    if not all(CARD_ID_RE.fullmatch(r) for r in c.get("related", [])): raise ValueError(f"{c['id']}: bad related id")
    imp = c.get("importance")
    if not isinstance(imp, dict) or set(imp) != {*CRITERIA, "why"}:
        raise ValueError(f"{c['id']}: importance needs {sorted(CRITERIA)} and why")
    if not all(imp[k] in (0, 1, 2, 3) for k in CRITERIA): raise ValueError(f"{c['id']}: importance criteria are 0-3")
    if not isinstance(imp["why"], str) or not imp["why"].strip(): raise ValueError(f"{c['id']}: importance.why is empty")


def check_pages(pages: dict) -> None:
    """pages: {"<printed page>": {"facts": ["...", ...]}} or {"skip": "why there is nothing to examine"}."""
    for p, v in pages.items():
        if not p.isdigit(): raise ValueError(f"page key {p!r} is not a page number")
        if set(v) == {"facts"}:
            if not (v["facts"] and all(isinstance(f, str) and f.strip() for f in v["facts"])): raise ValueError(f"page {p}: empty facts")
            if len(v["facts"]) > 99: raise ValueError(f"page {p}: more than 99 facts")
        elif not (set(v) == {"skip"} and isinstance(v["skip"], str) and v["skip"].strip()):
            raise ValueError(f"page {p}: give either facts or a skip reason")


def fact_ids(pages: dict) -> list[str]:
    return [f"p{int(p):03d}.f{k:02d}" for p, v in sorted(pages.items(), key=lambda x: int(x[0])) for k in range(1, len(v.get("facts", [])) + 1)]


def check_chapter(data: dict) -> None:
    check_pages(data.get("pages", {}))
    known = set(fact_ids(data.get("pages", {})))
    for c in data["cards"]:
        check_card(c)
        missing = [f for f in c["facts"] if f not in known]
        if missing: raise ValueError(f"{c['id']}: tests facts that are not in the page list: {missing}")


def calibration(cards: list[dict]) -> dict:
    """Tier shares of a set of cards, with a warning when ratings look inflated (a writer rating page by page tends to
    call everything important; across the specialty only about a quarter of facts are must-know)."""
    n = len(cards) or 1
    share = {t: sum(tier(c) == t for c in cards) / n for t in TIERS}
    warn = []
    if share["A"] > 0.40: warn.append(f"{share['A']:.0%} of cards are tier A (expected about 20-35%): rate against the whole specialty")
    if len(cards) >= 10 and share["C"] == 0: warn.append("no tier C card: background facts should be rated low")
    return {"cards": len(cards), "share": share, "warnings": warn}


def load_chapters(bank_dir: Path) -> dict[int, dict]:
    out = {}
    for f in sorted(bank_dir.glob("ch*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        check_chapter(data)
        out[data["chapter"]] = data
    return out


def load_bank(bank_dir: Path) -> dict[str, dict]:
    cards = {}
    for data in load_chapters(bank_dir).values():
        for c in data["cards"]:
            if c["id"] in cards: raise ValueError(f"duplicate card id {c['id']}")
            cards[c["id"]] = c
    return cards


def merge_cards(bank_file: Path, chapter: int, title: str, new: dict) -> tuple[int, int]:
    """Add or replace page facts (by page) and cards (by id) in one chapter's bank file; returns (added, replaced)."""
    data = json.loads(bank_file.read_text(encoding="utf-8")) if bank_file.exists() else {"chapter": chapter, "title": title, "pages": {}, "cards": []}
    check_pages(new.get("pages", {}))
    data["pages"].update({str(int(p)): v for p, v in new.get("pages", {}).items()})
    data["pages"] = dict(sorted(data["pages"].items(), key=lambda x: int(x[0])))
    have = {c["id"]: i for i, c in enumerate(data["cards"])}
    added = replaced = 0
    for c in new.get("cards", []):
        if c.get("chapter") != chapter: raise ValueError(f"{c.get('id')} is not chapter {chapter}")
        if c["id"] in have: data["cards"][have[c["id"]]] = c; replaced += 1
        else: have[c["id"]] = len(data["cards"]); data["cards"].append(c); added += 1
    data["cards"].sort(key=lambda c: c["id"])
    check_chapter(data)
    bank_file.parent.mkdir(parents=True, exist_ok=True)
    bank_file.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return added, replaced


def coverage(data: dict | None, book_pages: list[int]) -> dict:
    """How much of a chapter is examinable: pages with facts or a skip reason, and facts tested by at least one card."""
    data = data or {"pages": {}, "cards": []}
    pages = data["pages"]
    tested = {f for c in data["cards"] for f in c["facts"]}
    facts = fact_ids(pages)
    return {"pages": len(book_pages), "pages_done": sum(str(p) in pages for p in book_pages),
            "pages_missing": [p for p in book_pages if str(p) not in pages],
            "skipped": {p: v["skip"] for p, v in pages.items() if "skip" in v},
            "facts": len(facts), "facts_untested": [f for f in facts if f not in tested], "cards": len(data["cards"])}


# ---------- pages -> facts + cards (the prompt only; the cards are written by Claude or ChatGPT and added with merge_cards) ----------

def book_page(text: str) -> int | None:
    """Printed page number from a page's running head: '2    CHAPTER 1 ...' or '... HISTORY      3'."""
    head = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    m = re.match(r"(\d{1,4})\s", head) or re.search(r"\s(\d{1,4})$", head)
    return int(m[1]) if m else None


def page_texts(pdf: Path) -> list[dict]:
    """Every page with text, numbered by its printed page; a page without a running head (a full-page table or figure)
    takes the chapter's usual offset between PDF page and printed page."""
    raw = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], check=True, capture_output=True, text=True).stdout
    pages = [{"pdf_page": i, "page": book_page(t), "text": t.rstrip()} for i, t in enumerate(raw.split("\f"), 1) if t.strip()]
    offsets = Counter(p["page"] - p["pdf_page"] for p in pages if p["page"] is not None)
    off = offsets.most_common(1)[0][0] if offsets else 0
    for p in pages:
        if p["page"] is None or p["page"] - p["pdf_page"] != off: p["page"] = p["pdf_page"] + off
    return pages


QA_RULES = """\
You turn pages of the book into the question bank of a board oral exam (a viva), for one student who will be
examined by voice. Use ONLY what these pages say: no outside facts, numbers, doses or drug names.
NOTHING ON THE PAGES MAY BE LOST: work in two steps.

STEP 1, FACTS. For every page, list every examinable fact on it as short, faithful statements, in page order (a
definition, a list item, a number, a step, an indication, a complication, a table row...). A page with nothing to
examine (a full-page figure without text, a contents list, a blank page) gets "skip" with the reason instead.
Fact ids are pPPP.fNN: printed page, then the fact's number on that page (01, 02, ...).

STEP 2, CARDS. Write short viva questions until EVERY fact is tested by at least one card (list them in "facts").
- q: one short spoken question, as a board examiner says it ("What is...?", "Classify...", "How would you manage...?",
  "What are the complications of...?"), at most about 20 words. No multiple choice, no "which of the following", no
  symbols (write "more than", not ">"). Types: recall, list, why (mechanism), case (a one-line patient -> what now),
  compare (X versus Y), value (a number or threshold the page gives).
- level, the rung on the viva ladder the examiner climbs in each topic: 1 knowledge (what is it, define, list),
  2 understanding (why, mechanism, interpret, classify), 3 management (assess, decide, operate, what next),
  4 complications, outcomes and evidence (what goes wrong, results, controversy). Write cards on every rung the
  pages support, so a topic can be climbed.
- a: the model answer, SHORT: a phrase or one short sentence, at most about 20 words (for a list, just the items),
  in the page's own facts. If a fact needs a long answer, split it into several short cards.
- points: 1-4 key points the student must say for full marks (names, numbers, thresholds, as the page words them).
- topic: the page's heading (the viva topic the card belongs to; keep the same wording for the same heading).
- page and id: the printed page of the card's main fact; id chNN.pPPP.NN (01, 02 ... in page order).
- related: ids of cards on the same idea (so a failure on one brings the others forward).

IMPORTANCE (rate every card; the study order is built from it, never what is left out)
Score each criterion 0-3 for a cardiothoracic surgeon and a board examiner, judged against the WHOLE specialty, not
this page. The tool computes the score and the tier (A must know, B should know, C nice to know) from them.
{criteria}
- why: one line giving the reason (e.g. "missed tamponade kills; a classic viva question").
- Be strict: across the book only about a quarter of cards are tier A. History-taking details, background and
  rarities are rated low even when the page spends many words on them; a short line that can save a life is rated high.
  Low-importance facts still get their cards: they are asked later, not dropped.

Reply with ONLY one JSON object:
{{"pages": {{"<page>": {{"facts": ["...", ...]}} or {{"skip": "reason"}}, ...}},
 "cards": [{{"id", "chapter", "page", "topic", "type", "level", "q", "a", "points", "facts": ["pPPP.fNN", ...],
            "importance": {{"safety", "decision", "frequency", "exam", "core", "why"}}, "related"}}, ...]}}
"""


def qa_prompt(chapter: int, title: str, pages: list[dict]) -> str:
    body = "\n\n".join(f"=== book page {p['page']} (pdf page {p['pdf_page']}) ===\n{p['text']}" for p in pages)
    crit = "\n".join(f"- {k} (weight {w:.0%}): {d}" for k, (w, d) in CRITERIA.items())
    return f"{QA_RULES.format(criteria=crit)}\nBook: {BOOK}. Chapter {chapter}: {title}.\n\n{body}\n"


# ---------- state ----------

def load_state(path: Path) -> dict:
    st = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"schema": 1, "cards": {}, "sessions": []}
    st.setdefault("vivas", [])
    return st


def save_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def fsrs_card(entry: dict) -> Card:
    return Card.from_dict(entry["fsrs"])


def scheduler_for(card: dict) -> Scheduler:
    return SCHEDULERS[tier(card)]


def retrievability(entry: dict, now: datetime) -> float:
    return SCHEDULER.get_card_retrievability(fsrs_card(entry), current_datetime=now)


# ---------- session plan: a viva of topics ----------

def topic_key(card: dict) -> tuple[int, str]:
    return card["chapter"], card["topic"].strip().lower()


def plan_session(bank: dict, state: dict, now: datetime, topics: int = FULL_VIVA, new: int = 12,
                 chapters: list[int] | None = None, viva: str | None = None, tiers: list[str] | None = None,
                 mode: str = "exam", sid: str | None = None) -> dict:
    """Plan a viva: the most urgent topics, each a short climb of up to five questions.

    Urgency of a card: due (1 + forgetting x importance, +1 for a confident error), new (importance, only within `new`
    and `tiers`). A topic's urgency is the sum of its most urgent cards; topics already examined today are left out
    (the topic sheet). Inside a topic the questions go up the ladder (level 1 to 4). Scope: `chapters`, one `viva`
    (critical, cardiac, congenital, thoracic) or, by default, the whole book. Up to two leeches are taught at the end.
    """
    if mode not in ("exam", "practice"): raise ValueError("mode is exam or practice")
    chs = set(chapters or []) | set(VIVAS[viva][1] if viva else ())
    pool = {i: c for i, c in bank.items() if not chs or c["chapter"] in chs}
    cards, today = state["cards"], now.date().isoformat()
    asked_today = {(t["chapter"], t["topic"]) for v in state["vivas"] if v["date"] == today for t in v["topics"]}
    leeches = sorted(i for i in pool if cards.get(i, {}).get("leech"))[:2]
    due = {i for i in pool if i in cards and not cards[i].get("leech") and datetime.fromisoformat(cards[i]["fsrs"]["due"]) <= now + DUE_AHEAD}
    fresh = {i for i in pool if i not in cards and (not tiers or tier(pool[i]) in tiers)}

    def urgency(i):
        if i in due: return 1 + (1 - retrievability(cards[i], now)) * weight(pool[i]) + (1 if cards[i].get("confident_error") else 0)
        return importance_score(pool[i]["importance"]) / 100 if i in fresh else 0

    by_topic: dict[tuple, list[str]] = {}
    for i in due | fresh:
        if topic_key(pool[i]) not in asked_today: by_topic.setdefault(topic_key(pool[i]), []).append(i)
    ranked = sorted(by_topic, key=lambda k: (-sum(sorted(map(urgency, by_topic[k]), reverse=True)[:Q_PER_TOPIC]), k))
    chosen, budget = [], new
    for k in ranked:
        if len(chosen) == topics: break
        old = sorted((i for i in by_topic[k] if i in due), key=lambda i: (-urgency(i), i))[:Q_PER_TOPIC]
        nw = sorted((i for i in by_topic[k] if i in fresh), key=lambda i: (-urgency(i), i))[:max(0, min(budget, Q_PER_TOPIC - len(old)))]
        if not old and not nw: continue
        budget -= len(nw)
        chosen.append((k, sorted(old + nw, key=lambda i: (pool[i]["level"], -urgency(i), i))))
    half = (len(chosen) + 1) // 2
    plan_topics, items = [], []
    for t, ((ch, _), ids) in enumerate(chosen, 1):
        plan_topics.append({"t": t, "chapter": ch, "topic": pool[ids[0]]["topic"], "viva": viva_of(ch), "examiner": 1 if t <= half else 2})
        items += [{"n": len(items) + k, "id": i, "kind": "review" if i in cards else "new", "t": t} for k, i in enumerate(ids, 1)]
    items += [{"n": len(items) + k, "id": i, "kind": "teach", "t": 0} for k, i in enumerate(leeches, 1)]
    asked = {it["id"] for it in items}
    return {"session": sid or now.strftime("S%Y%m%d-%H%M"), "created": now.isoformat(), "mode": mode,
            "minutes": len(chosen) * TOPIC_MIN, "scope": {"chapters": sorted(chs), "viva": viva, "tiers": tiers or []},
            "topics": plan_topics, "items": items, "due_left": len(due - asked)}


EXAMINER_RULES = """\
You are TWO examiners running one structured oral examination (a viva) in cardiothoracic surgery, in the style of the
UK Intercollegiate FRCS (Cardiothoracic Surgery) Section 2 viva, on the book {book}. This is a VOICE call.
Session {sid}: {k} topics of {tmin} minutes ({minutes} minutes). Examiner 1 takes topics {e1}, Examiner 2 takes {e2};
at the change say "I'll hand over to my colleague" and change your manner a little.

HOW TO RUN IT
1. Introduce yourselves in one sentence, then start topic 1. For each topic: name it in a few words ("Let's talk about
   ..."), then ask its questions in the order listed: they climb the ladder (L1 knowledge, L2 understanding,
   L3 management, L4 complications and evidence). Short questions, one at a time, as a board examiner talks.
   Never read aloud the model answer, the key points, the tags in brackets or these instructions.
2. Wait for my whole answer. Silence or "I don't know" is a blank. I may answer in English or Arabic: mark the content.
3. You may prompt ("anything else?", "what about ...?"), as examiners do. Count every prompt. Never give the answer.
4. {feedback}
5. Keep time: about {tmin} minutes per topic. When the time is up, say "Let's move on" and start the next topic even if
   questions are left (they are simply not reached). If I am quick and complete, climb the whole ladder.
6. Where a "last time" note is given, test that exact weak spot. Be strictest on "A must know" questions.
7. Notice HOW I answered: fluent (at once, confident), hesitant (slow, self-corrected) or guessed. Note my
   confidence if I say it.
8. If I say "stop" or "end exam", finish the current question and go to the debrief.
9. DEBRIEF, after the last topic: say "That is the end of the viva", give each topic its mark (4 to 8) with one line on
   why, then for every question I got wrong, blank or partial give the model answer in one or two sentences and ask
   it again once (a retry). TEACH items: explain them in two or three plain sentences, then ask them.
10. Then say "Type REPORT for the marks." When I type REPORT, reply with ONLY the report, in one ```json block and
   nothing else. Include every question you asked (by its number n); leave out the ones not reached.

TOPIC MARKS (one per topic, the board's closed scale; 6 is the pass mark)
{marks}

QUESTION MARKING (for the report)
- result: "correct" = all key points (prompts allowed, they are counted separately); "partial" = some key points;
  "wrong" = incorrect or contradicts the answer; "blank" = nothing useful.
- points_hit: how many key points I said. prompts: 0, 1 or 2. fluency: "fluent" | "hesitant" | "guessed".
- confidence: "sure" | "unsure" | null (only if I said it). note: one short line on what I mixed up or missed, else "".
- retry: null, or {{"result": ..., "points_hit": ..., "prompts": ...}} for a question asked again in the debrief.

REPORT FORMAT
{{"session": "{sid}",
 "topics": [{{"t": 1, "mark": 6, "comment": "safe, needed prompting on the classification"}}],
 "items": [{{"n": 1, "result": "partial", "points_hit": 1, "prompts": 1, "fluency": "hesitant", "confidence": null,
            "note": "forgot class IV", "retry": null}}]}}
"""
FEEDBACK = {
    "exam": "As in the real exam, give NO feedback during the viva: no \"correct\", no corrections, no teaching; just "
            "\"OK\" or \"thank you\" and the next question, with a neutral manner. All feedback waits for the debrief.",
    "practice": "Practice mode: after each answer, say in one or two sentences what was right and what was missing, "
                "from the model answer, then go on.",
}


def examiner_prompt(plan: dict, bank: dict, state: dict) -> str:
    tps = plan["topics"]
    e1 = [str(t["t"]) for t in tps if t["examiner"] == 1]
    e2 = [str(t["t"]) for t in tps if t["examiner"] == 2]
    out = [EXAMINER_RULES.format(book=BOOK, sid=plan["session"], k=len(tps), tmin=TOPIC_MIN, minutes=plan["minutes"],
                                 e1=", ".join(e1) or "-", e2=", ".join(e2) or "none (Examiner 1 does all)",
                                 feedback=FEEDBACK[plan["mode"]],
                                 marks="\n".join(f"  {m} {d}" for m, d in sorted(MARKS.items(), reverse=True)))]
    for t in [*tps, {"t": 0}]:
        its = [it for it in plan["items"] if it["t"] == t["t"]]
        if not its: continue
        out.append(f"TOPIC {t['t']} (Examiner {t['examiner']}): {t['topic']} [{VIVAS[t['viva']][0]}, Ch{t['chapter']}]"
                   if t["t"] else "TEACH (in the debrief; not marked as a topic)")
        for it in its:
            c, entry = bank[it["id"]], state["cards"].get(it["id"], {})
            ti = tier(c)
            tag = [f"L{c['level']}", f"{ti} {TIERS[ti]}", it["kind"], f"p{c['page']}"]
            if entry.get("notes"): tag.append("last time: " + entry["notes"][-1]["note"])
            pts = "\n".join(f"       - {p}" for p in c["points"])
            out.append(f"  {it['n']}. [{' · '.join(tag)}]\n     Q: {c['q']}\n     Model answer: {c['a']}\n"
                       f"     Key points ({len(c['points'])}):\n{pts}")
        out.append("")
    return "\n".join(out)


# ---------- report -> ratings and viva marks ----------

def parse_report(text: str) -> dict:
    """The report as pasted: a bare JSON object, or one inside a ```json block with chat around it."""
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    raw = m[1] if m else text[text.find("{"): text.rfind("}") + 1]
    rep = json.loads(raw)
    if not isinstance(rep.get("items"), list): raise ValueError("report has no items list")
    for it in rep["items"]:
        if it.get("result") not in RESULTS: raise ValueError(f"item {it.get('n')}: result must be one of {RESULTS}")
        if it.get("fluency", "fluent") not in FLUENCY: raise ValueError(f"item {it.get('n')}: bad fluency")
        if it.get("confidence") not in (None, *CONFIDENCE): raise ValueError(f"item {it.get('n')}: bad confidence")
        if it.get("retry") is not None and it["retry"].get("result") not in RESULTS: raise ValueError(f"item {it['n']}: bad retry")
    for t in rep.setdefault("topics", []):
        if t.get("mark") not in MARKS: raise ValueError(f"topic {t.get('t')}: mark must be 4-8")
    return rep


def rate(item: dict, n_points: int, lapses: int = 0) -> tuple[Rating, str]:
    """One spoken answer -> FSRS rating, with the reason in words.

    Again: wrong, blank, less than half the key points, or right only after two prompts.
    Hard:  partial (half or more), one prompt, or a correct guess.
    Good:  correct but hesitant, unsure or not every key point; a once-failed card never gets more than Good.
    Easy:  every key point, at once, no prompt, not unsure.
    """
    if item.get("override") in (1, 2, 3, 4): return Rating(item["override"]), "set by the owner"
    res, prompts = item["result"], int(item.get("prompts", item.get("hints")) or 0)
    if res in ("wrong", "blank"): return Rating.Again, res
    hit = item.get("points_hit")
    cov = 1.0 if hit is None and res == "correct" else min(1.0, (hit or 0) / max(1, n_points))
    if res == "partial":
        return (Rating.Hard, f"partial, {hit}/{n_points} points") if cov >= 0.5 and prompts < 2 else (Rating.Again, f"partial, {hit}/{n_points} points")
    if prompts >= 2: return Rating.Again, "correct only after two prompts"
    if prompts == 1: return Rating.Hard, "correct after a prompt"
    if item.get("fluency") == "guessed": return Rating.Hard, "correct guess"
    if item.get("fluency") == "hesitant" or item.get("confidence") == "unsure" or cov < 1: return Rating.Good, "correct, not fluent or not complete"
    if lapses > 0: return Rating.Good, "correct and fluent (failed before, so not Easy)"
    return Rating.Easy, "correct, fluent, complete"


def auto_mark(answers: list[tuple[dict, Rating, dict]]) -> int:
    """A topic's mark from its questions, as a cross-check of the examiner's mark (and the mark when none was given).
    A confident wrong answer on a must-know question is dangerous: 4. Otherwise the importance-weighted quality of the
    answers, with 8 only for a topic climbed to its top rung."""
    if not answers: return 4
    if any(r == Rating.Again and it.get("confidence") == "sure" and tier(c) == "A" for c, r, it in answers): return 4
    val = {Rating.Again: 0, Rating.Hard: 0.5, Rating.Good: 0.85, Rating.Easy: 1}
    q = sum(val[r] * weight(c) for c, r, _ in answers) / sum(weight(c) for c, _, _ in answers)
    top = max(c["level"] for c, r, _ in answers if r >= Rating.Good) if any(r >= Rating.Good for _, r, _ in answers) else 0
    return 8 if q >= 0.9 and top >= 3 else 7 if q >= 0.75 else 6 if q >= 0.55 else 5 if q >= 0.3 else 4


def _review(entry: dict | None, rating: Rating, when: datetime, sch: Scheduler = SCHEDULER) -> dict:
    card = fsrs_card(entry) if entry else Card(card_id=1, due=when)
    was_learned = entry is not None and entry["fsrs"].get("last_review") is not None
    card, _ = sch.review_card(card, rating, review_datetime=when)
    e = dict(entry or {"reps": 0, "lapses": 0, "history": [], "notes": []})
    e["fsrs"] = card.to_dict()
    e["reps"] += 1
    if rating == Rating.Again and was_learned: e["lapses"] += 1
    return e


def mark(plan: dict, report: dict, state: dict, bank: dict, now: datetime) -> dict:
    """Apply a session's report to the state (in place): FSRS for every question, the viva marks for every topic.
    Returns {"rows": one per card, "viva": the topic marks and the result}."""
    sid = plan["session"]
    if report.get("session") not in (None, sid): raise ValueError(f"report is for {report['session']}, plan is {sid}")
    if sid in state["sessions"]: raise ValueError(f"{sid} is already marked")
    state.setdefault("vivas", [])
    by_n = {it["n"]: it for it in plan["items"]}
    first, second = now - RETRY_GAP, now
    rows, failed, per_topic = [], [], {}
    for it in report["items"]:
        p = by_n.get(it["n"])
        if not p: raise ValueError(f"report item n={it['n']} is not in the plan")
        cid, c = p["id"], bank[p["id"]]
        entry = state["cards"].get(cid)
        rating, why = rate(it, len(c["points"]), entry["lapses"] if entry else 0)
        if p["kind"] == "teach" and rating == Rating.Easy: rating, why = Rating.Good, why + " (taught today)"
        if p["t"]: per_topic.setdefault(p["t"], []).append((c, rating, it))
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
    given = {t["t"]: t for t in report.get("topics", [])}
    topics = []
    for t in plan["topics"]:
        if t["t"] not in per_topic: continue
        am = auto_mark(per_topic[t["t"]])
        g = given.get(t["t"])
        topics.append({"t": t["t"], "chapter": t["chapter"], "topic": t["topic"].strip().lower(), "viva": t["viva"],
                       "mark": g["mark"] if g else am, "auto": am, "comment": g.get("comment", "") if g else "marked from the answers"})
    viva = {"s": sid, "date": now.date().isoformat(), "mode": plan["mode"], "topics": topics}
    if topics:
        viva["total"], viva["pass_total"] = sum(t["mark"] for t in topics), PASS_MARK * len(topics)
        viva["result"] = "pass" if viva["total"] >= viva["pass_total"] else "fail"
        viva["bad_fails"] = sum(t["mark"] == 4 for t in topics)
    state["vivas"].append(viva)
    state["sessions"].append(sid)
    return {"rows": rows, "viva": viva}


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


# ---------- pages an agent can read (no FSRS maths, no big JSON) ----------

PAGE = "VIVA.md"  # the one page: the next viva + the spaced repetition, for the owner and for any agent


def status_lines(bank: dict, state: dict, now: datetime) -> list[str]:
    """The spaced repetition, already computed: what is due when, memory per topic, viva results, weakest cards."""
    cards = state["cards"]
    st = status(bank, state, now)
    learned = {i: e for i, e in cards.items() if i in bank}
    out = [f"{len(bank)} cards in the bank; {len(learned)} learned, {len(bank) - len(learned)} not started yet. "
           f"Due now: **{st['due_now']}**; due within 7 days: {st['due_week']}. Vivas marked: {st['sessions']}.", ""]
    if learned:
        days = Counter(datetime.fromisoformat(e["fsrs"]["due"]).date() for e in learned.values())
        out += ["| Day (UTC) | Cards due |", "|---|---|"]
        out += [f"| {d.isoformat()} | {days[d]} |" for d in sorted(days) if d <= (now + timedelta(days=14)).date()] or ["| - | 0 |"]
        out += [""]
    out += ["| Chapter | Cards | A / B / C | Not started (A) | Due now | Leeches |", "|---|---|---|---|---|---|"]
    out += [f"| {ch} | {s['cards']} | {s['A']} / {s['B']} / {s['C']} | {s['new']} ({s['new_A']}) | {s['due']} | {s['leech']} |"
            for ch, s in sorted(st["chapters"].items())]
    topics: dict[tuple, list] = {}
    for i, c in bank.items(): topics.setdefault((c["chapter"], c["topic"]), []).append(i)
    rows = []
    for (ch, t), ids in topics.items():
        got = [i for i in ids if i in learned]
        if got:
            rec = sum(retrievability(learned[i], now) for i in got) / len(got)
            rows.append((rec, f"| Ch{ch} {t} | {len(got)}/{len(ids)} | {rec:.0%} | "
                              f"{sum(datetime.fromisoformat(learned[i]['fsrs']['due']) <= now + DUE_AHEAD for i in got)} |"))
    if rows:
        out += ["", "### Memory per topic (learned cards only, weakest first)", "",
                "| Topic | Learned | Recall now | Due now |", "|---|---|---|---|"] + [r for _, r in sorted(rows)]
    vivas = state.get("vivas", [])
    if vivas:
        out += ["", "### Viva results", "", "| Date | Session | Topic marks | Total / needed | Result |", "|---|---|---|---|---|"]
        out += [f"| {v['date']} | {v['s']} | {', '.join(str(t['mark']) for t in v['topics'])} | "
                f"{v.get('total', '-')} / {v.get('pass_total', '-')} | {v.get('result', '-')} |" for v in vivas[-10:]]
        out += [""] + [f"- {VIVAS[k][0]}: average topic mark {m} (pass {PASS_MARK})" for k, m in st["vivas"].items()]
    if st["weakest"]:
        out += ["", "### Weakest cards", "", "| Card | Tier | Recall now | Lapses | Question |", "|---|---|---|---|---|"]
        out += [f"| {w['id']} | {w['tier']} | {w['recall']:.0%} | {w['lapses']} | {w['q']} |" for w in st["weakest"]]
    return out


def viva_page(bank: dict, state: dict, now: datetime, plan: dict | None) -> str:
    """ONE page with everything: how to use it, the next viva (self-contained) and the spaced repetition, so the owner
    and any agent need a single link and never the JSON or the FSRS maths."""
    out = ["<!-- generated by tools/examiner.py: do not edit -->", "# Your viva and spaced repetition", "",
           f"Updated {now.strftime('%Y-%m-%d %H:%M')} UTC.", "",
           "**How to use:** open a Claude or ChatGPT voice chat, give it this page (the link, or paste it) and say "
           "\"start the viva\". At the end type `REPORT` and paste the JSON to Claude Code (the Mcqs- session): it marks "
           "it, updates the schedule and rewrites this page with the next viva.", "",
           "**If you are an AI:** this page is everything. Part 1 is your job: you are the examiner, the rules, questions, "
           "model answers and key points are all there. Part 2 is the spaced repetition, already computed by "
           "`tools/examiner.py` (FSRS): read it, never work it out yourself, and do not open any other file of the repository.", ""]
    if plan:
        n = sum(1 for it in plan["items"] if it["t"])
        out += [f"## Part 1: the viva ({plan['session']})", "",
                f"Planned {plan['created'][:10]}: {len(plan['topics'])} topics, {plan['minutes']} minutes, {n} questions, "
                f"{plan['mode']} mode.", "", "```text", examiner_prompt(plan, bank, state).rstrip(), "```", ""]
    else:
        out += ["## Part 1: the viva", "", "No viva is planned: nothing is due and no new card is left. Ask Claude Code for one.", ""]
    out += ["## Part 2: spaced repetition (already computed)", ""] + status_lines(bank, state, now)
    out += ["", "How it works: [README.md](README.md). All questions, readable: [bank/](bank/)."]
    return "\n".join(out) + "\n"


# ---------- readable Q&A page ----------

def qa_markdown(data: dict) -> str:
    """One chapter's bank as a plain question-and-answer page to read (GitHub renders it): topics in book order,
    must-know first inside each topic. Written next to the JSON by `add` / `export`; the JSON stays the source."""
    cards = data["cards"]
    first_page: dict[str, int] = {}
    for c in cards: first_page[c["topic"]] = min(first_page.get(c["topic"], c["page"]), c["page"])
    tiers = {t: sum(tier(c) == t for c in cards) for t in TIERS}
    out = [f"# Chapter {data['chapter']}: {data['title']}", "",
           f"{len(cards)} questions and short answers from the book ({BOOK}), every fact of the chapter covered. "
           f"A must know {tiers['A']}, B should know {tiers['B']}, C nice to know {tiers['C']}. "
           "Generated from `ch%02d.json` (`tools/examiner.py export`): edit the JSON, not this page." % data["chapter"], ""]
    for topic in sorted(first_page, key=lambda t: (first_page[t], t)):
        tc = sorted((c for c in cards if c["topic"] == topic), key=lambda c: (tier(c), c["level"], c["id"]))
        out += [f"## {topic} (p{first_page[topic]})", ""]
        for k, c in enumerate(tc, 1):
            out += [f"{k}. **Q:** {c['q']}  ", f"   **A:** {c['a']}  ", f"   _{tier(c)} {TIERS[tier(c)]} · p{c['page']}_", ""]
    return "\n".join(out)


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
    last: dict[str, list[int]] = {}
    for v in state.get("vivas", [])[::-1]:  # each viva's average over its most recent 10 topic marks
        for t in v["topics"]:
            if len(last.setdefault(t["viva"], [])) < 10: last[t["viva"]].append(t["mark"])
    return {"chapters": by_ch, "due_now": sum(s["due"] for s in by_ch.values()),
            "due_week": sum(1 for d in due_at.values() if d <= now + timedelta(days=7)),
            "weakest": [{"id": i, "q": bank[i]["q"], "tier": tier(bank[i]), "recall": round(retrievability(cards[i], now), 2),
                         "lapses": cards[i]["lapses"]} for i in weak],
            "vivas": {k: round(sum(m) / len(m), 1) for k, m in last.items()},
            "recent": [{k: v.get(k) for k in ("s", "date", "total", "pass_total", "result")} for v in state.get("vivas", [])[-5:]],
            "sessions": len(state["sessions"])}
