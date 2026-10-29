#!/usr/bin/env python3
"""Kafu image-lesson queue: see which packages have all their images in Google Drive.

ChatGPT saves one image per question into the shared Drive folder, named <QID>.png.
A package (4 questions, queue/<PKG>.json) is complete when every QID has an image there.
Builders start only when every package is complete (preflight.py images).

  watch.py status                progress of every package: question numbers, images, ledger state, what is missing
  watch.py missing               only the questions still without an image (number and QID), and the total
  watch.py state PKG             the package's ledger state (waiting / building / delivered / failed)
  watch.py download PKG DIR      save the package's images as DIR/<QID>.png
  watch.py get DIR QID...        save only these images as DIR/<QID>.png (split builds)
  watch.py claim PKG [NOTE]      ledger: building (Head only; the ledger lives in the data folder)
  watch.py deliver PKG [NOTE]    ledger: delivered
  watch.py fail PKG REASON       ledger: failed (a later run retries it)

Reads the folder through its public "anyone with the link" view: no Drive login needed.
"""
import calendar
import html
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from kafu_data import CONFIG, LEDGER, QUEUE  # noqa: E402  (the run's data folder, never the repository)
STALE_HOURS = 3          # a "building" claim older than this is retried (a normal build takes about 40 minutes)
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp")


# ---------- Google Drive (public folder) ----------
def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def list_drive(folder_id, depth=0, every=None):
    """{file name: file id} for the folder and its subfolders (first seen wins on duplicates).
    every: an optional list that receives every (name, id), duplicates included."""
    page = fetch(f"https://drive.google.com/embeddedfolderview?id={folder_id}").decode("utf-8", "ignore")
    files = {}
    for m in re.finditer(r'<a href="https://drive\.google\.com/(file/d|drive/folders)/([\w-]+)[^"]*"[^>]*>.*?'
                         r'<div class="flip-entry-title">([^<]*)</div>', page, re.S):
        kind, fid, name = m.group(1), m.group(2), html.unescape(m.group(3)).strip()
        if kind == "drive/folders":
            if depth < 3:
                for k, v in list_drive(fid, depth + 1, every).items():
                    files.setdefault(k, v)
        else:
            files.setdefault(name, fid)
            if every is not None:
                every.append((name, fid))
    return files


def images_by_qid(files):
    out = {}
    for name, fid in files.items():
        stem, ext = os.path.splitext(name)
        if ext.lower() in IMAGE_EXT:
            out.setdefault(stem.strip().upper(), (fid, name))
    return out


def download(fid):
    return fetch(f"https://drive.usercontent.google.com/download?id={fid}&export=download&confirm=t")


# ---------- queue + ledger ----------
def packages():
    pk = {p.stem: json.loads(p.read_text()) for p in QUEUE.glob("*.json")}
    def num(v):
        s = str(v if v is not None else "")
        return (0, int(s), "") if s.isdigit() else (1, 0, s)

    def first(k):
        q = pk[k]
        return (str(q.get("book_id", "")), num(q.get("chapter_id")), num(q["items"][0].get("number")), k)
    return {k: pk[k] for k in sorted(pk, key=first)}   # book, chapter, question order (ch4 before ch36, Q9 before Q10)


def ledger():
    return json.loads(LEDGER.read_text()) if LEDGER.exists() else {}


def set_state(pkg, state, note=""):
    from kafu_data import require_data_folder
    require_data_folder()
    led = ledger()
    led[pkg] = {"state": state, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "note": note}
    LEDGER.write_text(json.dumps(led, indent=1, ensure_ascii=False) + "\n")
    print(f"{pkg}: {state}")


def is_open(entry):
    """True when the package still needs work."""
    if not entry:
        return True
    if entry["state"] == "failed":
        return True
    if entry["state"] == "building":
        age = time.time() - calendar.timegm(time.strptime(entry["at"], "%Y-%m-%dT%H:%M:%SZ"))
        return age > STALE_HOURS * 3600
    return False


def image_warning(im):
    """A short note when an image is not the expected landscape 3:2 of at least 1200 px (a sign of a wrong or broken image)."""
    w, h = im.size
    if w < 1200 or not 1.3 <= w / h <= 1.7:
        return "  WARNING: unexpected size, check this image before using it"
    return ""


def numbers(q):
    """'Q155-158' (or the question numbers as listed) for a package."""
    ns = [str(it.get("number")) for it in q["items"] if it.get("number") is not None]
    if not ns:
        return ""
    return f"Q{ns[0]}" if len(ns) == 1 else f"Q{ns[0]}-{ns[-1]}"


def building_count(led):
    n = 0
    for e in led.values():
        if e.get("state") == "building" and not is_open(e):
            n += 1
    return n



def progress():
    imgs = images_by_qid(list_drive(CONFIG["drive_folder_id"]))
    led = ledger()
    rows = []
    for pkg, q in packages().items():
        qids = [it["qid"].upper() for it in q["items"]]
        have = [x for x in qids if x in imgs]
        rows.append((pkg, len(have), len(qids), led.get(pkg), [x for x in qids if x not in imgs]))
    return rows, imgs


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        rows, imgs = progress()
        pk = packages()
        for pkg, n, total, entry, missing in rows:
            state = entry["state"] if entry else "waiting"
            if entry and entry["state"] == "building" and is_open(entry):
                state = "STALE"
            num = {it["qid"].upper(): it.get("number") for it in pk[pkg]["items"]}
            miss = " ".join(f"Q{num[m]}" for m in missing[:8]) + (" ..." if len(missing) > 8 else "")
            print(f"{pkg:22s} {numbers(pk[pkg]):10s} images {n:>2}/{total:<2} {state:10s} {('missing: ' + miss) if missing else ''}")
        total_q = sum(r[2] for r in rows)
        print(f"Drive folder: {len(imgs)} image(s); {sum(r[1] for r in rows)}/{total_q} needed; builders running: {building_count(ledger())}")
    elif cmd == "missing":
        rows, imgs = progress()
        pk = packages()
        miss = [(it.get("number"), it["qid"]) for pkg, _, _, _, m in rows for it in pk[pkg]["items"] if it["qid"].upper() in m]
        for n, q in miss:
            print(f"Q{n}  {q}")
        print(f"missing {len(miss)} of {sum(r[2] for r in rows)}")
    elif cmd == "state":
        e = ledger().get(sys.argv[2])
        print(e["state"] if e else "waiting")
    elif cmd == "download":
        pkg, dest = sys.argv[2], Path(sys.argv[3])
        dest.mkdir(parents=True, exist_ok=True)
        imgs = images_by_qid(list_drive(CONFIG["drive_folder_id"]))
        from PIL import Image
        for it in packages()[pkg]["items"]:
            qid = it["qid"].upper()
            if qid not in imgs:
                sys.exit(f"missing image for {qid}")
            data = download(imgs[qid][0])
            im = Image.open(io.BytesIO(data))
            im.load()
            im.convert("RGB").save(dest / f"{it['qid']}.png")
            print(f"{it['qid']}.png  {im.size[0]}x{im.size[1]}  from {imgs[qid][1]}{image_warning(im)}")
    elif cmd == "get":
        # get <dest> QID...: download only these images (for a split build of part of a package)
        dest = Path(sys.argv[2]); dest.mkdir(parents=True, exist_ok=True)
        imgs = images_by_qid(list_drive(CONFIG["drive_folder_id"]))
        from PIL import Image
        for qid in (q.upper() for q in sys.argv[3:]):
            if qid not in imgs:
                sys.exit(f"missing image for {qid}")
            im = Image.open(io.BytesIO(download(imgs[qid][0])))
            im.load()
            im.convert("RGB").save(dest / f"{qid}.png")
            print(f"{qid}.png  {im.size[0]}x{im.size[1]}  from {imgs[qid][1]}{image_warning(im)}")
    elif cmd in ("claim", "deliver", "fail"):
        pkg = sys.argv[2]
        if pkg not in packages():
            sys.exit(f"unknown package {pkg}")
        note = " ".join(sys.argv[3:])
        set_state(pkg, {"claim": "building", "deliver": "delivered", "fail": "failed"}[cmd], note)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
