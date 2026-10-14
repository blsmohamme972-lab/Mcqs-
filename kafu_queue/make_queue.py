#!/usr/bin/env python3
"""Turn a chapter export into image-lesson packages for ChatGPT.

  make_queue.py split EXPORT --pkg-prefix BAILEY-CH1 [--size 10] [--qids Q1,Q2] [--already-live]
      Copies the export to exports/ and writes queue/<PKG>.json skeletons
      (one per config batch_size questions, default 4: small packages build in parallel and finish fast) with the question facts and an empty "prompt".
  make_queue.py render PKG     After the prompts are written: checks them and writes queue/<PKG>.md,
                               the page ChatGPT reads.
  make_queue.py check          Checks every package.
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUEUE = HERE / "queue"
CONFIG = json.loads((HERE / "config.json").read_text())


def answer_text(q):
    for o in q.get("options", []):
        label = (o.get("label") or o.get("key") or o.get("letter") or "") if isinstance(o, dict) else ""
        text = (o.get("text") or o.get("value") or "") if isinstance(o, dict) else str(o)
        if label.strip().upper() == str(q.get("answer", "")).strip().upper():
            return text.strip()
    letters = "ABCDEFGH"
    a = str(q.get("answer", "")).strip().upper()
    opts = q.get("options", [])
    if a in letters and letters.index(a) < len(opts):
        o = opts[letters.index(a)]
        return (o.get("text") if isinstance(o, dict) else str(o)).strip()
    return ""


def split(a):
    exp = json.loads(Path(a.export).read_text())
    (HERE / "exports").mkdir(exist_ok=True)
    dest = HERE / "exports" / Path(a.export).name
    if Path(a.export).resolve() != dest.resolve():
        shutil.copy(a.export, dest)
    qs = exp["questions"]
    if a.qids:
        keep = set(a.qids.split(","))
        qs = [q for q in qs if q["id"] in keep]
    QUEUE.mkdir(exist_ok=True)
    for i in range(0, len(qs), a.size):
        chunk = qs[i:i + a.size]
        first, last = chunk[0]["source_number"], chunk[-1]["source_number"]
        pkg = f"{a.pkg_prefix}-Q{int(first):02d}-{int(last):02d}" if str(first).isdigit() and str(last).isdigit() \
            else f"{a.pkg_prefix}-{i // a.size + 1:02d}"
        items = [{
            "qid": q["id"], "number": q.get("source_number"), "stem": q.get("stem", ""),
            "options": q.get("options", []), "answer": q.get("answer"), "answer_text": answer_text(q),
            "explanation": q.get("explanation", ""), "has_book_images": bool(q.get("images")),
            "prompt": "",
        } for q in chunk]
        out = {"package_id": pkg, "book_id": exp["scope"]["book_id"], "chapter_id": exp["scope"]["chapter_id"],
               "chapter_title": exp["scope"].get("chapter_title", ""), "export": f"exports/{dest.name}",
               "already_live": a.already_live, "items": items}
        path = QUEUE / f"{pkg}.json"
        if path.exists():
            print(f"skip {pkg}: exists")
            continue
        path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
        print(f"{pkg}: {len(items)} questions")


def problems(q):
    bad = []
    for it in q["items"]:
        p = it.get("prompt", "")
        if not p.strip():
            bad.append(f"{it['qid']}: no prompt")
        elif "Answer -->" not in p:
            bad.append(f"{it['qid']}: prompt lacks the 'Answer -->' banner")
        elif len(p) > 3500:
            bad.append(f"{it['qid']}: prompt longer than 3500 chars")
    return bad


def render(pkg):
    q = json.loads((QUEUE / f"{pkg}.json").read_text())
    bad = problems(q)
    if bad:
        sys.exit("\n".join(bad))
    lines = [f"# {pkg}: {len(q['items'])} images", "",
             f"Rules: see GPT.md. Save each image to the Drive folder {CONFIG['drive_folder_url']}",
             "named exactly `<QID>.png` (the QID in the heading). One image per question, landscape 3:2.", ""]
    for it in q["items"]:
        lines += [f"## {it['qid']}  (question {it['number']})", "", "```", it["prompt"].strip(), "```",
                  "", f"Save as: `{it['qid']}.png`", ""]
    (QUEUE / f"{pkg}.md").write_text("\n".join(lines))
    print(f"wrote queue/{pkg}.md")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("split")
    s.add_argument("export")
    s.add_argument("--pkg-prefix", required=True)
    s.add_argument("--size", type=int, default=CONFIG["batch_size"])
    s.add_argument("--qids")
    s.add_argument("--already-live", action="store_true")
    r = sub.add_parser("render")
    r.add_argument("pkg")
    sub.add_parser("check")
    a = ap.parse_args()
    if a.cmd == "split":
        split(a)
    elif a.cmd == "render":
        render(a.pkg)
    else:
        any_bad = False
        for p in sorted(QUEUE.glob("*.json")):
            bad = problems(json.loads(p.read_text()))
            print(f"{p.stem}: {'OK' if not bad else '; '.join(bad)}")
            any_bad |= bool(bad)
        sys.exit(1 if any_bad else 0)


if __name__ == "__main__":
    main()
