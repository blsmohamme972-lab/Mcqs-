#!/usr/bin/env python3
"""Voice examiner: a board-style viva by ChatGPT or Claude voice call; the report sets your FSRS spaced repetition.

  examiner.py pages    ch01 [--pages 2-6]      page text + the bank-writing rules -> work/examiner/qa/<ch>_pPPP-PPP.prompt.md
  examiner.py add      ch01 bank.json          check the page facts and cards (importance, ladder level, facts tested)
                                               and merge them into examiner/bank/ch01.json; prints coverage and tiers
  examiner.py export   [ch01 ...]              the bank as a readable Q&A page -> examiner/bank/ch01.md (add does it too)
  examiner.py coverage [ch01 ...]              pages without facts, facts no card tests (nothing in the book is lost)
  examiner.py session  [--topics 6] [--viva critical|cardiac|congenital|thoracic] [--chapters 1 2] [--new 12]
                       [--tier A] [--mode exam|practice]
                                               plan a viva (5-minute topics, two examiners; 6 topics = a full viva)
                                               -> examiner/sessions/<sid>.plan.json and the examiner prompt
                                               -> work/examiner/<sid>.prompt.md (paste it, then talk). Most urgent
                                               topics first: due cards by forgetting x importance, new by importance
  examiner.py show     <sid>                   the plan with questions, answers and key points (to grade a transcript)
  examiner.py mark     <sid> report.json       apply the report: topic marks 4-8 (pass 6), FSRS for every question
  examiner.py rank     [--chapters 1] [--top 20]  the bank by importance: tier shares, warnings, the top cards
  examiner.py status                           due cards, tiers, viva marks per viva, recent results, weakest cards
  examiner.py publish                          rewrite examiner/VIVA.md (session and mark do it too): the one page with
                                               the next viva and the spaced repetition, read instead of the JSON
Needs py-fsrs 6.3.2 (`pip install fsrs==6.3.2`, the engine the app's Fsrs.kt is verified against) and pdftotext.
"""
import argparse, json, sys
from datetime import timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from examiner import lib  # noqa: E402

HOME = ROOT / "examiner"
BANK, SESSIONS, STATE = HOME / "bank", HOME / "sessions", HOME / "state.json"
WORK = ROOT / "work" / "examiner"
PDFS = ROOT / "Cardiothoracic_Surgery_Chapters"


def chapter_pdf(ch) -> tuple[int, str, Path]:
    n = int(str(ch).removeprefix("ch"))
    pdf = next(PDFS.glob(f"Chapter_{n:02d}_*.pdf"), None)
    if not pdf: sys.exit(f"no PDF for chapter {n}")
    return n, pdf.stem.split("_", 2)[2].replace("_", " "), pdf


def load_plan(sid: str) -> dict:
    p = SESSIONS / f"{sid}.plan.json"
    if not p.exists(): sys.exit(f"no plan {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def print_coverage(n: int, data) -> None:
    _, _, pdf = chapter_pdf(n)
    cv = lib.coverage(data, [p["page"] for p in lib.page_texts(pdf)])
    tested = cv["facts"] - len(cv["facts_untested"])
    print(f"ch{n:02d}: pages {cv['pages_done']}/{cv['pages']} done ({len(cv['skipped'])} skipped), "
          f"facts tested {tested}/{cv['facts']}, {cv['cards']} cards")
    if cv["pages_missing"]: print(f"  pages still to write: {', '.join(map(str, cv['pages_missing']))}")
    if cv["facts_untested"]: print(f"  facts no card tests: {', '.join(cv['facts_untested'])}")


def open_plan(state: dict):
    """The newest planned viva that is not marked yet (the one VIVA.md shows)."""
    for p in sorted(SESSIONS.glob("S*.plan.json"), reverse=True):
        plan = json.loads(p.read_text(encoding="utf-8"))
        if plan["session"] not in state["sessions"]: return plan
    return None


def publish(bank: dict, state: dict, now, plan=None) -> None:
    """VIVA.md: the next viva (self-contained) and the spaced repetition on one page, what the owner and agents read."""
    (HOME / lib.PAGE).write_text(lib.viva_page(bank, state, now, plan or open_plan(state)), encoding="utf-8")


def new_session(bank, state, at, a):
    plan = lib.plan_session(bank, state, at, a.topics, a.new, a.chapters, a.viva, a.tier, a.mode)
    if not plan["items"]: return None
    SESSIONS.mkdir(parents=True, exist_ok=True); WORK.mkdir(parents=True, exist_ok=True)
    (SESSIONS / f"{plan['session']}.plan.json").write_text(json.dumps(plan, indent=1) + "\n", encoding="utf-8")
    (WORK / f"{plan['session']}.prompt.md").write_text(lib.examiner_prompt(plan, bank, state), encoding="utf-8")
    return plan


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["pages", "add", "export", "coverage", "session", "show", "mark", "rank", "status", "publish"])
    ap.add_argument("args", nargs="*"); ap.add_argument("--pages")
    ap.add_argument("--topics", type=int, default=lib.FULL_VIVA); ap.add_argument("--viva", choices=list(lib.VIVAS))
    ap.add_argument("--new", type=int, default=12); ap.add_argument("--chapters", type=int, nargs="*")
    ap.add_argument("--tier", nargs="*", choices=list(lib.TIERS)); ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--mode", choices=["exam", "practice"], default="exam")
    a = ap.parse_args(); now = lib.utcnow()

    if a.cmd == "pages":
        n, title, pdf = chapter_pdf(a.args[0]); pages = lib.page_texts(pdf)
        if a.pages:
            lo, _, hi = a.pages.partition("-"); lo, hi = int(lo), int(hi or lo)
            pages = [p for p in pages if lo <= p["page"] <= hi]
        if not pages: sys.exit("no pages in that range")
        out = WORK / "qa" / f"ch{n:02d}_p{pages[0]['page']:03d}-{pages[-1]['page']:03d}.prompt.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(lib.qa_prompt(n, title, pages), encoding="utf-8")
        print(f"{len(pages)} pages -> {out}\nwrite the facts and cards from it, then: examiner.py add ch{n:02d} <bank.json>")

    elif a.cmd == "add":
        n, title, _ = chapter_pdf(a.args[0])
        new = json.loads(Path(a.args[1]).read_text(encoding="utf-8"))
        added, replaced = lib.merge_cards(BANK / f"ch{n:02d}.json", n, title, new)
        chapters = lib.load_chapters(BANK); lib.load_bank(BANK)  # the whole bank must still load (no duplicate ids)
        cal = lib.calibration(chapters[n]["cards"])
        print(f"ch{n:02d}: {added} cards added, {replaced} replaced; tiers " + ", ".join(f"{t} {v:.0%}" for t, v in cal["share"].items()))
        for w in cal["warnings"]: print("WARNING:", w)
        print_coverage(n, chapters[n])
        (BANK / f"ch{n:02d}.md").write_text(lib.qa_markdown(chapters[n]), encoding="utf-8")

    elif a.cmd == "export":
        chapters = lib.load_chapters(BANK)
        for n in [int(str(c).removeprefix("ch")) for c in a.args] or sorted(chapters):
            out = BANK / f"ch{n:02d}.md"; out.write_text(lib.qa_markdown(chapters[n]), encoding="utf-8"); print(out)

    elif a.cmd == "coverage":
        chapters = lib.load_chapters(BANK)
        for ch in a.args or sorted(chapters) or range(1, 18): print_coverage(int(str(ch).removeprefix("ch")), chapters.get(int(str(ch).removeprefix("ch"))))

    elif a.cmd == "session":
        bank, state = lib.load_bank(BANK), lib.load_state(STATE)
        if not bank: sys.exit("the bank is empty: make cards first (examiner.py pages, then add)")
        plan = new_session(bank, state, now, a)
        if not plan: sys.exit("nothing to ask: no card is due and no new card is left in that scope")
        publish(bank, state, now, plan); out = HOME / lib.PAGE
        kinds = [i["kind"] for i in plan["items"]]
        print(f"{plan['session']} ({plan['mode']}): {len(plan['topics'])} topics, {plan['minutes']} min; "
              f"{kinds.count('review')} review, {kinds.count('new')} new, {kinds.count('teach')} teach "
              f"({plan['due_left']} due left for later) -> {out}")
        for t in plan["topics"]: print(f"  {t['t']}. [examiner {t['examiner']}] Ch{t['chapter']} {t['topic']}")

    elif a.cmd == "show":
        print(lib.examiner_prompt(load_plan(a.args[0]), lib.load_bank(BANK), lib.load_state(STATE)))

    elif a.cmd == "mark":
        sid, plan = a.args[0], load_plan(a.args[0])
        report = lib.parse_report(Path(a.args[1]).read_text(encoding="utf-8"))
        bank, state = lib.load_bank(BANK), lib.load_state(STATE)
        res = lib.mark(plan, report, state, bank, now)
        lib.save_state(STATE, state)
        (SESSIONS / f"{sid}.report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        v = res["viva"]
        for t in v["topics"]:
            print(f"topic {t['t']} Ch{t['chapter']} {t['topic']}: {t['mark']}/8 ({lib.MARKS[t['mark']].split(':')[0]};"
                  f" from the answers {t['auto'] if t['auto'] else '-'}) {t['comment']}")
        if v["topics"]: print(f"viva: {v['total']} of {v['pass_total']} needed -> {v['result'].upper()}"
                              + (f", {v['bad_fails']} bad fail(s)" if v["bad_fails"] else ""))
        for r in res["rows"]:
            print(f"{r['n'] or '-':>3} {r['id']:16} {r['rating']:6} next {r['due'][:10]}  {r['why']}"
                  + (f" | {r['retry']}" if r.get("retry") else "") + ("  LEECH: will be taught" if r.get("leech") else ""))
        asked = {it["n"] for it in report["items"]}
        skipped = [it["id"] for it in plan["items"] if it["n"] not in asked]
        if skipped and report["items"]: print(f"not reached (still due): {', '.join(skipped)}")
        if v.get("partial"):
            print("topic marks only: the viva result is saved, no card was rescheduled; the session stays open for the full report")
        nxt = new_session(bank, state, now + timedelta(days=1), a)  # the next viva is ready on GitHub, planned for tomorrow
        publish(bank, state, now, nxt)
        print(f"next viva: {nxt['session'] if nxt else 'none (nothing due or new)'}; wrote examiner/{lib.PAGE}")

    elif a.cmd == "publish":
        bank, state = lib.load_bank(BANK), lib.load_state(STATE)
        publish(bank, state, now); print(f"wrote examiner/{lib.PAGE}")

    elif a.cmd == "rank":
        cards = [c for c in lib.load_bank(BANK).values() if not a.chapters or c["chapter"] in a.chapters]
        cal = lib.calibration(cards)
        print(f"{cal['cards']} cards; tiers " + ", ".join(f"{t} {lib.TIERS[t]} {v:.0%}" for t, v in cal["share"].items()))
        for w in cal["warnings"]: print("WARNING:", w)
        for c in sorted(cards, key=lambda c: (-lib.importance_score(c["importance"]), c["id"]))[:a.top]:
            print(f"  {lib.importance_score(c['importance']):3} {lib.tier(c)} L{c['level']} {c['id']:15} {c['q']}  ({c['importance']['why']})")

    else:
        bank, state = lib.load_bank(BANK), lib.load_state(STATE)
        st = lib.status(bank, state, now)
        print(f"due now {st['due_now']}, due within a week {st['due_week']}, sessions marked {st['sessions']}")
        for ch, s in sorted(st["chapters"].items()):
            print(f"  ch{ch:02d}: {s['cards']} cards (A {s['A']}, B {s['B']}, C {s['C']}), {s['new']} new"
                  f" ({s['new_A']} must-know not started), {s['due']} due, {s['leech']} leech")
        for k, m in st["vivas"].items(): print(f"  {lib.VIVAS[k][0]}: average topic mark {m} (pass {lib.PASS_MARK})")
        for r in st["recent"]: print(f"  {r['date']} {r['s']}: {r.get('total')}/{r.get('pass_total')} {r.get('result') or ''}")
        for w in st["weakest"]:
            print(f"  weak {w['id']} ({w['tier']}) recall {w['recall']:.0%} lapses {w['lapses']}: {w['q']}")


if __name__ == "__main__":
    main()
