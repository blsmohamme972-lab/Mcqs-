#!/usr/bin/env python3
"""Checks that must pass before the next stage starts (Head Department). Exit code 0 only when everything is OK.

  preflight.py export FILE            the app export passes the project's own adapt_exports (integrity rows, content hash,
                                      fingerprint, book identity) and every question has a key that resolves
  preflight.py images PREFIX [--fast] every question of the packages PREFIX-* has exactly one image in Drive named
                                      <QID>.png, and (without --fast) each opens and is landscape 3:2 of at least 1200 px
  preflight.py zips DIR PREFIX        (PREFIX may be a comma list) every MCARDS_<PKG>_r1.zip in DIR passes validate_package, is at most
                                      max_package_zip_mb, and holds exactly its package's QIDs; lists packages still missing
  preflight.py coverage DIR PREFIX    the merged parts in DIR pass validate_package, are at most merge_part_mb, and
                                      together hold every question of PREFIX exactly once; prints byte size and sha256.
                                      DIR and PREFIX may each be a comma list (parts merged in two rounds, a run split
                                      over several prefixes such as BL-CH1,BL-CH1B); held questions (<data>/held) are
                                      listed apart and do not fail the check
  preflight.py sheet PREFIX OUTDIR [--qids Q,Q] [--images-dir DIR]
                                      review sheets for the Head: one PNG per 8 questions, each row = question number, QID,
                                      the key, then the image's own title strip and answer banner strip (cheap to look at)

The project code is read from KAFU_MOUNTAIN (default: the repository this folder is in). Point it at an up-to-date
checkout of main so the checks are the same as the bot's.
"""
import hashlib
import io
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import watch  # noqa: E402

MOUNTAIN = Path(os.environ.get("KAFU_MOUNTAIN", HERE.parent))
sys.path.insert(0, str(MOUNTAIN))
CONFIG = watch.CONFIG
NAME_RE = re.compile(r"^Q\d{9}\.png$")


def pkgs(prefix):
    """The packages of one prefix or of a comma list of prefixes (a run cut into several splits)."""
    pres = [x for x in prefix.split(",") if x]
    pk = {k: v for k, v in watch.packages().items() if any(k.startswith(x + "-") for x in pres)}
    if not pk:
        sys.exit(f"no packages {prefix}-* in {watch.QUEUE}")
    return pk


def held_qids():
    from kafu_data import DATA
    return sorted(f.stem for f in (DATA / "held").glob("Q*.json")) if (DATA / "held").is_dir() else []


def check_export(path):
    from motioncards.lib import core
    try:
        env = json.loads(Path(path).read_text())
        ad = core.adapt_exports([env])
    except Exception as e:  # noqa: BLE001
        print(f"FAIL export rejected by adapt_exports: {e} (ask the owner for the full app export, with question_integrity)")
        return False
    bad = []
    for q in ad.questions:
        try:
            core.resolve_answer(q)
        except Exception as e:  # noqa: BLE001
            bad.append(f"{q.get('id')}: {e}")
    nums = [q.get("source_number") for q in env["questions"]]
    print(f"export OK: {len(ad.questions)} questions, integrity rows {len(ad.integrity)}, "
          f"book {ad.book.get('id') if isinstance(ad.book, dict) else ''}, numbers {nums[0]}..{nums[-1]}")
    if len(set(map(str, nums))) != len(nums):
        bad.append("duplicate source_number")
    flagged = [q for q in env["questions"] if str(q.get("flag") or "").strip()]
    for q in flagged:                                  # the app's own warnings: read them BEFORE any image is drawn
        print(f"FLAG {q.get('id')} (number {q.get('source_number')}, key {q.get('answer')}): {q['flag']}")
    if flagged:
        print(f"{len(flagged)} flagged question(s): review each key now; a clearly wrong key is fixed by the owner in the app "
              f"and exported again before the painter pages are made")
    for b in bad:
        print("FAIL", b)
    return not bad


def check_images(prefix, fast):
    every = []
    watch.list_drive(CONFIG["drive_folder_id"], every=every)
    by = {}
    for name, fid in every:
        stem = os.path.splitext(name)[0].strip().upper()
        by.setdefault(stem[:10], []).append((name, fid))
    bad, total = [], 0
    for pkg, q in pkgs(prefix).items():
        for it in q["items"]:
            total += 1
            qid = it["qid"].upper()
            have = by.get(qid, [])
            exact = [x for x in have if NAME_RE.match(x[0]) and x[0][:10].upper() == qid]
            if not have:
                bad.append(f"Q{it.get('number')} {qid}: missing")
            elif len(have) > 1:
                bad.append(f"Q{it.get('number')} {qid}: {len(have)} files {[n for n, _ in have]} (keep one, named {qid}.png)")
            elif not exact:
                bad.append(f"Q{it.get('number')} {qid}: wrong name {have[0][0]!r} (must be {qid}.png)")
            elif not fast:
                from PIL import Image
                try:
                    im = Image.open(io.BytesIO(watch.download(have[0][1])))
                    im.load()
                    w = watch.image_warning(im)
                    if w:
                        bad.append(f"Q{it.get('number')} {qid}: {im.size[0]}x{im.size[1]}{w}")
                except Exception as e:  # noqa: BLE001
                    bad.append(f"Q{it.get('number')} {qid}: does not open ({type(e).__name__})")
    for b in bad:
        print("FAIL", b)
    print(f"images: {total - len(bad)}/{total} OK" + ("" if fast else " (opened and measured)") +
          f"; Drive lists {len(every)} file(s)")
    return not bad


def check_zips(d, prefix):
    from motioncards.lib import package as P
    cap = CONFIG["max_package_zip_mb"] * 1024 * 1024
    bad, done = [], 0
    pk = pkgs(prefix)
    for pkg, q in pk.items():
        f = Path(d) / f"MCARDS_{pkg}_r1.zip"
        if not f.exists():
            bad.append(f"{pkg}: no ZIP yet")
            continue
        try:
            m = P.validate_package(f)
        except Exception as e:  # noqa: BLE001
            bad.append(f"{pkg}: validate failed {e}")
            continue
        want = {it["qid"] for it in q["items"]}
        got = {a["qid"] for a in m["animations"]}
        if got != want:
            bad.append(f"{pkg}: lessons {sorted(got)} != package {sorted(want)} (missing {sorted(want - got)})")
        elif f.stat().st_size > cap:
            bad.append(f"{pkg}: {f.stat().st_size} B is over {CONFIG['max_package_zip_mb']} MB")
        else:
            done += 1
    for b in bad:
        print("FAIL", b)
    print(f"zips: {done}/{len(pk)} packages OK")
    return not bad


def check_coverage(d, prefix):
    from motioncards.lib import package as P
    cap = CONFIG["merge_part_mb"] * 1024 * 1024
    held = set(held_qids())
    want = [it["qid"] for q in pkgs(prefix).values() for it in q["items"]]
    seen, bad = [], []
    parts = sorted(f for x in d.split(",") if x for f in Path(x).glob("MCARDS_*_r1.zip"))
    if not parts:
        bad.append(f"no MCARDS_*_r1.zip in {d}")
    for f in parts:
        m = P.validate_package(f)
        qs = [a["qid"] for a in m["animations"]]
        seen += qs
        size = f.stat().st_size
        sha = hashlib.sha256(f.read_bytes()).hexdigest()
        print(f"{f.name}  {size} bytes  {len(qs)} lessons  sha256 {sha}")
        if size > cap:
            bad.append(f"{f.name}: over {CONFIG['merge_part_mb']} MB")
    dup = sorted({q for q in seen if seen.count(q) > 1})
    miss = sorted(set(want) - set(seen))
    extra = sorted(set(seen) - set(want) - held)
    if held:
        print(f"held (not built, the owner fixes the key in the app first): {sorted(held - set(seen))}")
    for label, xs in (("twice", dup), ("missing", miss), ("not in this chapter", extra)):
        if xs:
            bad.append(f"{label}: {xs}")
    for b in bad:
        print("FAIL", b)
    print(f"coverage: {len(set(seen) & set(want))}/{len(want)} questions, each once: {not dup}")
    return not bad


def sheet(prefix, out, only=None, images_dir=None):
    from PIL import Image, ImageDraw, ImageFont
    items = [it for q in pkgs(prefix).values() for it in q["items"] if not only or it["qid"] in only]
    imgs = {} if images_dir else watch.images_by_qid(watch.list_drive(CONFIG["drive_folder_id"]))
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    except OSError:
        font = ImageFont.load_default()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    W, made, missing = 1000, [], []
    for start in range(0, len(items), 8):
        rows = []
        for it in items[start:start + 8]:
            qid = it["qid"].upper()
            head = Image.new("RGB", (W, 44), "white")
            d = ImageDraw.Draw(head)
            d.text((10, 8), f"Q{it.get('number')}  {qid}   KEY: {it.get('answer_text', '')[:60]}", fill="black", font=font)
            rows.append(head)
            try:
                if images_dir:
                    im = Image.open(Path(images_dir) / f"{qid}.png")
                else:
                    im = Image.open(io.BytesIO(watch.download(imgs[qid][0])))
                im = im.convert("RGB")
            except Exception:  # noqa: BLE001
                missing.append(qid)
                rows.append(Image.new("RGB", (W, 60), (255, 220, 220)))
                continue
            w, h = im.size
            for box in ((0, 0, w, int(h * 0.16)), (0, int(h * 0.80), w, h)):
                crop = im.crop(box)
                rows.append(crop.resize((W, max(1, int(crop.size[1] * W / w)))))
            rows.append(Image.new("RGB", (W, 10), (40, 40, 40)))
        sheet_img = Image.new("RGB", (W, sum(r.size[1] for r in rows)), "white")
        y = 0
        for r in rows:
            sheet_img.paste(r, (0, y))
            y += r.size[1]
        f = out / f"sheet_{start // 8 + 1:02d}.png"
        sheet_img.save(f)
        made.append(f)
    for f in made:
        print(f)
    if missing:
        print("FAIL no image yet: " + " ".join(missing))
    print(f"{len(made)} sheet(s) for {len(items)} questions: look at each; every answer banner must state the KEY")
    return not missing


def main(a):
    if not a:
        sys.exit(__doc__)
    cmd = a[0]
    if cmd == "export":
        ok = check_export(a[1])
    elif cmd == "images":
        ok = check_images(a[1], "--fast" in a)
    elif cmd == "zips":
        ok = check_zips(a[1], a[2])
    elif cmd == "coverage":
        ok = check_coverage(a[1], a[2])
    elif cmd == "sheet":
        only = set(a[a.index("--qids") + 1].split(",")) if "--qids" in a else None
        idir = a[a.index("--images-dir") + 1] if "--images-dir" in a else None
        ok = sheet(a[1], a[2], only, idir)
    else:
        sys.exit(__doc__)
    print("PREFLIGHT", cmd, "OK" if ok else "FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main(sys.argv[1:])
