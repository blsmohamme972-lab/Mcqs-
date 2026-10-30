#!/usr/bin/env python3
"""Voice examiner: you answer aloud to ChatGPT or Claude, the report sets your FSRS spaced repetition.

  examiner.py pages   ch01 [--pages 2-6]       page text + the Q&A-writing rules -> work/examiner/qa/<ch>_pPPP-PPP.prompt.md
  examiner.py add     ch01 cards.json          check the written cards and merge them into examiner/bank/ch01.json
  examiner.py session [--minutes 20] [--new 8] [--chapters 1 2]
                                               plan the next exam -> examiner/sessions/<sid>.plan.json and the voice
                                               examiner prompt -> work/examiner/<sid>.prompt.md (paste it, then talk)
  examiner.py show    <sid>                    the plan with questions, answers and key points (to grade a transcript)
  examiner.py mark    <sid> report.json        apply the examiner's report: ratings, next due dates, related cards
  examiner.py status                           due now / this week, new and leech cards per chapter, weakest cards
Needs py-fsrs 6.3.2 (`pip install fsrs==6.3.2`, the engine the app's Fsrs.kt is verified against) and pdftotext.
"""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from examiner import lib  # noqa: E402

HOME = ROOT / "examiner"
BANK, SESSIONS, STATE = HOME / "bank", HOME / "sessions", HOME / "state.json"
WORK = ROOT / "work" / "examiner"


def chapter_pdf(ch: str) -> tuple[int, str, Path]:
    n = int(ch.removeprefix("ch"))
    pdf = next((ROOT / "Cardiothoracic_Surgery_Chapters").glob(f"Chapter_{n:02d}_*.pdf"), None)
    if not pdf: sys.exit(f"no PDF for chapter {n}")
    return n, pdf.stem.split("_", 2)[2].replace("_", " "), pdf


def load_plan(sid: str) -> dict:
    p = SESSIONS / f"{sid}.plan.json"
    if not p.exists(): sys.exit(f"no plan {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["pages", "add", "session", "show", "mark", "status"])
    ap.add_argument("args", nargs="*"); ap.add_argument("--pages"); ap.add_argument("--minutes", type=int, default=20)
    ap.add_argument("--new", type=int, default=8); ap.add_argument("--chapters", type=int, nargs="*")
    a = ap.parse_args(); now = lib.utcnow()

    if a.cmd == "pages":
        n, title, pdf = chapter_pdf(a.args[0]); pages = lib.page_texts(pdf)
        if a.pages:
            lo, _, hi = a.pages.partition("-"); lo, hi = int(lo), int(hi or lo)
            pages = [p for p in pages if p["page"] is not None and lo <= p["page"] <= hi]
        if not pages: sys.exit("no pages in that range")
        span = f"p{pages[0]['page'] or 0:03d}-{pages[-1]['page'] or 0:03d}"
        out = WORK / "qa" / f"ch{n:02d}_{span}.prompt.md"; out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(lib.qa_prompt(n, title, pages), encoding="utf-8")
        print(f"{len(pages)} pages -> {out}\nwrite the cards from it, then: examiner.py add ch{n:02d} <cards.json>")

    elif a.cmd == "add":
        n, title, _ = chapter_pdf(a.args[0])
        new = json.loads(Path(a.args[1]).read_text(encoding="utf-8"))
        added, replaced = lib.merge_cards(BANK / f"ch{n:02d}.json", n, title, new["cards"] if isinstance(new, dict) else new)
        lib.load_bank(BANK)  # the whole bank must still load (no duplicate ids across chapters)
        print(f"ch{n:02d}: {added} added, {replaced} replaced")

    elif a.cmd == "session":
        bank, state = lib.load_bank(BANK), lib.load_state(STATE)
        if not bank: sys.exit("the bank is empty: make cards first (examiner.py pages, then add)")
        plan = lib.plan_session(bank, state, now, a.minutes, a.new, a.chapters)
        if not plan["items"]: sys.exit("nothing to ask: no card is due and no new card is left")
        SESSIONS.mkdir(parents=True, exist_ok=True); WORK.mkdir(parents=True, exist_ok=True)
        (SESSIONS / f"{plan['session']}.plan.json").write_text(json.dumps(plan, indent=1) + "\n", encoding="utf-8")
        out = WORK / f"{plan['session']}.prompt.md"
        out.write_text(lib.examiner_prompt(plan, bank, state), encoding="utf-8")
        kinds = [i["kind"] for i in plan["items"]]
        print(f"{plan['session']}: {kinds.count('review')} review, {kinds.count('new')} new, {kinds.count('teach')} teach"
              f" ({plan['due_left']} due left for later) -> {out}")

    elif a.cmd == "show":
        print(lib.examiner_prompt(load_plan(a.args[0]), lib.load_bank(BANK), lib.load_state(STATE)))

    elif a.cmd == "mark":
        sid, plan = a.args[0], load_plan(a.args[0])
        report = lib.parse_report(Path(a.args[1]).read_text(encoding="utf-8"))
        bank, state = lib.load_bank(BANK), lib.load_state(STATE)
        rows = lib.mark(plan, report, state, bank, now)
        lib.save_state(STATE, state)
        (SESSIONS / f"{sid}.report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        for r in rows:
            print(f"{r['n'] or '-':>3} {r['id']:16} {r['rating']:6} next {r['due'][:10]}  {r['why']}"
                  + (f" | {r['retry']}" if r.get("retry") else "") + ("  LEECH: will be taught" if r.get("leech") else ""))
        asked = {it["n"] for it in report["items"]}
        skipped = [it["id"] for it in plan["items"] if it["n"] not in asked]
        if skipped: print(f"not reached (still due): {', '.join(skipped)}")

    else:
        bank, state = lib.load_bank(BANK), lib.load_state(STATE)
        st = lib.status(bank, state, now)
        print(f"due now {st['due_now']}, due within a week {st['due_week']}, sessions marked {st['sessions']}")
        for ch, s in sorted(st["chapters"].items()):
            print(f"  ch{ch:02d}: {s['cards']} cards, {s['new']} new, {s['due']} due, {s['leech']} leech")
        for w in st["weakest"]:
            print(f"  weak {w['id']} recall {w['recall']:.0%} lapses {w['lapses']}: {w['q']}")


if __name__ == "__main__":
    main()
