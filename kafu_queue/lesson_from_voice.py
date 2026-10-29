#!/usr/bin/env python3
"""Turn ChatGPT's voice scripts into lesson files (builder session).

  python3 /home/user/kq/kafu_queue/lesson_from_voice.py work/<PKG>/lessons <QID>... [--force]

Run it after the images are in work/<PKG>/lessons. For every QID with kafu_queue/voice/<QID>.json it writes
<QID>.lesson.json: the intro (question + answer), the lines and the remember line, the takeaway, Breeze, tempo 1.0, and the
camera shots worked out from the image size: shot 0 = the whole picture, shot n = the n-th scene line of the image prompt
(scenes run left to right, so scene n sits in the n-th vertical strip). Then YOU review it:
  - facts: every line must agree with the stem, key and explanation (fix a line only if it is wrong),
  - shots: look at the image; move a shot or spot if its scene is not where the strip guess put it.
An existing lesson file is kept unless --force. QIDs without a voice script are listed: write those lessons yourself.
The result is checked with the project's own check_lesson (KAFU_MOUNTAIN, default: the current directory).
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from kafu_data import VOICE  # noqa: E402


def shots_for(w, h, n):
    shots = [{"x": round(w / 2), "y": round(h / 2), "z": 1}]
    z = 1.8 if n <= 3 else 2.2
    hw, hh = w / (2 * z), h / (2 * z)
    for i in range(1, n + 1):
        cx = (i - 0.5) * w / n
        x = min(max(cx, hw), w - hw)
        y = min(max(0.45 * h, hh), h - hh)
        shots.append({"x": round(x), "y": round(y), "z": z, "spot": [round(cx), round(0.42 * h), round(w / n * 0.35)]})
    return shots


def main(a):
    force = "--force" in a
    a = [x for x in a if x != "--force"]
    if len(a) < 2:
        sys.exit(__doc__)
    d, qids = Path(a[0]), a[1:]
    sys.path.insert(0, os.environ.get("KAFU_MOUNTAIN", os.getcwd()))
    try:
        from motioncards.lib.lesson import check_lesson
    except ImportError:
        check_lesson = None
        print("note: motioncards.lib.lesson not found; run from the repository root to check the result")
    from PIL import Image
    made, own = [], []
    for q in qids:
        src, img, out = VOICE / f"{q}.json", d / f"{q}.png", d / f"{q}.lesson.json"
        if not src.exists():
            own.append(q)
            continue
        if out.exists() and not force:
            print(f"{q}: lesson file already there, kept")
            continue
        if not img.exists():
            sys.exit(f"{q}: no image {img}; get the images first")
        row = json.loads(src.read_text())
        L = row["lesson"]
        w, h = Image.open(img).size
        lesson = {"qid": q, "image": f"{q}.png", "takeaway": L["takeaway"], "engine": "breeze", "tempo": 1.0,
                  "question": L["question"], "answer": L["answer"], "shots": shots_for(w, h, len(row["scenes"])),
                  "lines": []}
        for ln in L["lines"]:
            x = {"text": ln["text"], "shot": int(ln["scene"]), "dir": ln["dir"]}
            if ln.get("say"):
                x["say"] = ln["say"]
            lesson["lines"].append(x)
        if check_lesson:
            check_lesson(lesson, q)
        out.write_text(json.dumps(lesson, indent=1, ensure_ascii=False) + "\n")
        made.append(q)
    print(f"written from voice scripts: {len(made)} ({' '.join(made)})")
    if own:
        print(f"no voice script, write these lessons yourself (LESSON_PROMPT step 5, at most 60 s): {' '.join(own)}")


if __name__ == "__main__":
    main(sys.argv[1:])
