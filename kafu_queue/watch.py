#!/usr/bin/env python3
"""Kafu image-lesson queue: see which packages have all their images in Google Drive.

ChatGPT saves one image per question into the shared Drive folder, named <QID>.png.
A package (about 4 questions, queue/<PKG>.json) is READY when every QID has an image there
and the ledger does not already show it as building or delivered.

  watch.py ready                 one line per ready package (at most max_concurrent_builders minus the ones building), or NONE
  watch.py status                progress of every package: question numbers, images, ledger state, what is missing
  watch.py builder-prompt PKG    the full prompt for a builder session (BUILDER_TEMPLATE.md filled in)
  watch.py gpt-prompts [N]       ChatGPT prompts for every missing image, N images per chat (default from config)
  watch.py download PKG DIR      save the package's images as DIR/<QID>.png
  watch.py get DIR QID...        save only these images as DIR/<QID>.png (split builds)
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
STALE_HOURS = 3          # a "building" claim older than this is retried (a normal build takes about 40 minutes)
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


def raw_base():
    repo = CONFIG["queue_repo"].replace("https://github.com/", "")
    return f"https://raw.githubusercontent.com/{repo}/{CONFIG['queue_branch']}/kafu_queue"


def builder_prompt(pkg):
    q = packages()[pkg]
    tpl = (HERE / "BUILDER_TEMPLATE.md").read_text()
    qids = " ".join(it["qid"] for it in q["items"])
    nums = ", ".join(str(it.get("number")) for it in q["items"])
    vals = {
        "PKG": pkg, "pkg_lower": pkg.lower(), "QIDS": qids, "NUMBERS": nums,
        "CHAPTER": f"{q.get('book_id', '')}, chapter {q.get('chapter_id', '')}: {q.get('chapter_title', '')}",
        "EXPORT": q["export"], "ALREADY_LIVE": "yes" if q.get("already_live") else "no",
        "BASE_BRANCH": CONFIG["lessons_base_branch"], "QUEUE_BRANCH": CONFIG["queue_branch"],
        "QUEUE_REPO": CONFIG["queue_repo"], "LESSONS_REPO_SLUG": CONFIG["lessons_repo_slug"],
    }
    return tpl.format(**vals)


GPT_HEADER = ('IMPORTANT - FRESH START: I deleted every image from earlier attempts. Ignore any images, files or results from '
              'previous chats or from your memory. Do not reuse, link to or re-upload any old image. The ONLY truth is what is '
              'in the Drive folder "Books" right now (not the trash): skip a QID only if <QID>.png is listed there now. '
              'Every image in this task must be newly generated in this chat.')


def gpt_prompts(per_chat):
    rows, _ = progress()
    pk = packages()
    missing = []   # (qid, pkg)
    for pkg, n, total, entry, miss in rows:
        if entry and entry["state"] == "delivered":
            continue
        missing += [(m, pkg) for m in miss]
    if not missing:
        print("No missing images.")
        return
    for i in range(0, len(missing), per_chat):
        chunk = missing[i:i + per_chat]
        pages = sorted({p for _, p in chunk})
        qids = ", ".join(q for q, _ in chunk)
        nums = ", ".join(str(next(it["number"] for it in pk[p]["items"] if it["qid"].upper() == q)) for q, p in chunk)
        print(f"===== CHAT {i // per_chat + 1} (questions {nums}) =====")
        print(GPT_HEADER)
        print()
        print(f'Task: make one teaching illustration per question and save it to my Google Drive folder "Books" ({CONFIG["drive_folder_url"]}).')
        print()
        print(f"First read the rules: {raw_base()}/GPT.md")
        print()
        print('Each QID\'s ready prompt is under its "## <QID>" heading in:')
        for pg in pages:
            print(f"- {raw_base()}/queue/{pg}.md")
        print()
        print(f"YOUR QIDs (only these, in this order): {qids}")
        print()
        print('For each QID: if <QID>.png is already in "Books", skip it. Otherwise generate the image from its prompt exactly as '
              'written (landscape 3:2, 1536x1024) and save it to "Books" in the same message, named exactly <QID>.png (capital Q, '
              'no extra words). Do not stop after generating: generate, then save, then go to the next QID. If a label is wrong or '
              'missing, regenerate once. Do not save drafts or duplicates. When finished, reply with one line: saved N/N and the '
              'QIDs you could not save. If you cannot save to Drive, say so plainly; do not claim it was saved.')
        print()


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
        room = max(0, CONFIG.get("max_concurrent_builders", 8) - building_count(ledger()))
        ready = [r for r in rows if r[1] == r[2] and is_open(r[3])]
        for pkg, n, total, _, _ in ready[:room]:
            print(f"READY {pkg} {n}/{total}")
        for pkg, n, total, _, _ in ready[room:]:
            print(f"WAIT {pkg} (builder limit {CONFIG.get('max_concurrent_builders', 8)} reached)")
        if not ready[:room]:
            print("NONE")
    elif cmd == "status":
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
    elif cmd == "builder-prompt":
        print(builder_prompt(sys.argv[2]))
    elif cmd == "gpt-prompts":
        gpt_prompts(int(sys.argv[2]) if len(sys.argv) > 2 else CONFIG.get("chatgpt_chunk", 5))
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
