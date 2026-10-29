#!/usr/bin/env python3
"""Turn a chapter export into image-lesson packages (the image prompts are written by ChatGPT: gpt_writer.py).

  make_queue.py split EXPORT --pkg-prefix GT-CH5 [--size 4] [--qids Q1,Q2] [--already-live]
      Copies the export to <data>/exports/ and writes <data>/queue/<PKG>.json (config batch_size questions each, default 4)
      with the question facts. Run preflight.py export EXPORT first: a broken export stops every builder.
  make_queue.py split-all BOOK EXPORT... [--size 4]
      Many chapters at once (files or ZIPs of them): each chapter gets its own prefix BOOK-CH<chapter_id>
      (e.g. GT-CH4, GT-CH36). Run preflight.py export on each file first.
  make_queue.py check          Checks every package: QIDs unique, key letter valid, answer text found; lists questions
                               with book images (the Head must look at those images, then mark them).
  make_queue.py inspected QID...   After LOOKING at a question's book images: mark it, so the builders may scaffold it.
"""
import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from kafu_data import CONFIG, EXPORTS, QUEUE, require_data_folder  # noqa: E402


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
    require_data_folder()
    exp = json.loads(Path(a.export).read_text())
    EXPORTS.mkdir(parents=True, exist_ok=True)
    dest = EXPORTS / Path(a.export).name
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
        } for q in chunk]
        out = {"package_id": pkg, "book_id": exp["scope"]["book_id"], "chapter_id": exp["scope"]["chapter_id"],
               "chapter_title": exp["scope"].get("chapter_title", ""), "export": dest.name,
               "already_live": a.already_live, "items": items}
        path = QUEUE / f"{pkg}.json"
        if path.exists():
            print(f"skip {pkg}: exists")
            continue
        path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
        print(f"{pkg}: {len(items)} questions")


def split_all(a):
    import tempfile
    import zipfile
    blobs = []
    tmp = Path(tempfile.mkdtemp())
    for f in a.exports:
        if f.lower().endswith(".zip"):
            with zipfile.ZipFile(f) as z:
                blobs += [z.read(n) for n in z.namelist() if n.lower().endswith(".json")]
        else:
            blobs.append(Path(f).read_bytes())
    done = set()
    for b in blobs:
        try:
            exp = json.loads(b.decode("utf-8"))
        except ValueError:
            continue
        if exp.get("export_type") != "kafu_mcq_text_export":
            continue
        book, ch = exp["scope"]["book_id"], exp["scope"]["chapter_id"]
        if (book, ch) in done:
            print(f"--- {book} chapter {ch}: already split from another file, skipped")
            continue
        done.add((book, ch))
        f = tmp / f"{book}-ch{ch}.export.json"          # one clear name per chapter, whatever the file was called
        f.write_bytes(b)
        print(f"--- {f.name}: chapter {ch}")
        split(argparse.Namespace(export=str(f), pkg_prefix=f"{a.book}-CH{ch}", size=a.size, qids=None,
                                 already_live=a.already_live))


def problems(q, seen=None):
    bad = []
    for it in q["items"]:
        if seen is not None:
            if it["qid"] in seen:
                bad.append(f"{it['qid']}: also in {seen[it['qid']]}")
            seen[it["qid"]] = q["package_id"]
        if not str(it.get("answer", "")).strip():
            bad.append(f"{it['qid']}: no answer key")
        if not it.get("answer_text", "").strip():
            bad.append(f"{it['qid']}: answer text not found for key {it.get('answer')!r}")
    return bad


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("split")
    s.add_argument("export")
    s.add_argument("--pkg-prefix", required=True)
    s.add_argument("--size", type=int, default=CONFIG["batch_size"])
    s.add_argument("--qids")
    s.add_argument("--already-live", action="store_true")
    m = sub.add_parser("split-all")
    m.add_argument("book")
    m.add_argument("exports", nargs="+")
    m.add_argument("--size", type=int, default=CONFIG["batch_size"])
    m.add_argument("--already-live", action="store_true")
    sub.add_parser("check")
    ins = sub.add_parser("inspected")
    ins.add_argument("qids", nargs="+")
    a = ap.parse_args()
    if a.cmd == "split":
        split(a)
    elif a.cmd == "split-all":
        split_all(a)
    elif a.cmd == "inspected":
        require_data_folder()
        left = set(a.qids)
        for p in sorted(QUEUE.glob("*.json")):
            q = json.loads(p.read_text())
            hit = [it for it in q["items"] if it["qid"] in left]
            for it in hit:
                it["book_images_inspected"] = True
                left.discard(it["qid"])
            if hit:
                p.write_text(json.dumps(q, indent=1, ensure_ascii=False) + "\n")
                print(f"{p.stem}: marked {[it['qid'] for it in hit]}")
        if left:
            sys.exit(f"not found: {sorted(left)}")
    else:
        any_bad, seen = False, {}
        for p in sorted(QUEUE.glob("*.json")):
            bad = problems(json.loads(p.read_text()), seen)
            books = [it["qid"] for it in json.loads(p.read_text())["items"] if it.get("has_book_images") and not it.get("book_images_inspected")]
            print(f"{p.stem}: {'OK' if not bad else '; '.join(bad)}" + (f"  BOOK IMAGES to look at: {books}" if books else ""))
            any_bad |= bool(bad)
        sys.exit(1 if any_bad else 0)


if __name__ == "__main__":
    main()
