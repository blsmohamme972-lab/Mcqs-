#!/usr/bin/env python3
"""Kafu image-lesson queue: see which packages have all their images in Google Drive.

ChatGPT saves one image per question into the shared Drive folder, named <QID>.png.
A package (8-10 questions, queue/<PKG>.json) is READY when every QID has an image there
and the ledger does not already show it as building or delivered.

  watch.py ready                 one line per ready package, or NONE
  watch.py status                progress of every package
  watch.py download PKG DIR      save the package's images as DIR/<QID>.png
  watch.py claim PKG [NOTE]      ledger: building (commit + push it right after)
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
QUEUE = Path(os.environ.get("KAFU_QUEUE_DIR", HERE / "queue"))
LEDGER = Path(os.environ.get("KAFU_LEDGER", HERE / "ledger.json"))
CONFIG = json.loads((HERE / "config.json").read_text())
STALE_HOURS = 6          # a "building" claim older than this is retried
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp")


# ---------- Google Drive (public folder) ----------
def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def list_drive(folder_id, depth=0):
    """{file name: file id} for the folder and its subfolders (newest wins on duplicates)."""
    page = fetch(f"https://drive.google.com/embeddedfolderview?id={folder_id}").decode("utf-8", "ignore")
    files = {}
    for m in re.finditer(r'<a href="https://drive\.google\.com/(file/d|drive/folders)/([\w-]+)[^"]*"[^>]*>.*?'
                         r'<div class="flip-entry-title">([^<]*)</div>', page, re.S):
        kind, fid, name = m.group(1), m.group(2), html.unescape(m.group(3)).strip()
        if kind == "drive/folders":
            if depth < 3:
                files.update(list_drive(fid, depth + 1))
        else:
            files.setdefault(name, fid)
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
    return {p.stem: json.loads(p.read_text()) for p in sorted(QUEUE.glob("*.json"))}


def ledger():
    return json.loads(LEDGER.read_text()) if LEDGER.exists() else {}


def set_state(pkg, state, note=""):
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
    if cmd == "ready":
        rows, _ = progress()
        ready = [r for r in rows if r[1] == r[2] and is_open(r[3])]
        for pkg, n, total, _, _ in ready:
            print(f"READY {pkg} {n}/{total}")
        if not ready:
            print("NONE")
    elif cmd == "status":
        rows, imgs = progress()
        for pkg, n, total, entry, missing in rows:
            state = entry["state"] if entry else "waiting"
            print(f"{pkg:28s} images {n:>2}/{total:<2} {state:10s} missing: {' '.join(missing[:6])}{' ...' if len(missing) > 6 else ''}")
        print(f"Drive folder: {len(imgs)} image(s)")
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
            print(f"{it['qid']}.png  {im.size[0]}x{im.size[1]}  from {imgs[qid][1]}")
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
