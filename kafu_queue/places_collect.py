#!/usr/bin/env python3
"""ChatGPT's picture notes -> the packages, so the builder sessions know what every picture shows when they write the voice.

  places_collect.py PREFIX [DIR]   read every places_*.txt in the Drive folder (or in DIR, files saved by hand), cut it
                                   into one note per QID, and store the note as "picture_notes" in that question's item of
                                   the PREFIX-* packages. Prints how many questions got notes and which are still without.
                                   Run it after the images are in, before bundle.py pack (the bundle carries the packages).

A note is the text from a line naming a QID up to the line naming the next QID (ChatGPT writes 4-7 short lines per image:
the real place and background, the main character and what it stands for, each other character's fact, the memory trick,
any extra fact). Notes are only a help for the voice: the facts still come from the stem, the key and the explanation.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import watch  # noqa: E402
from kafu_data import QUEUE, require_data_folder  # noqa: E402

QID = re.compile(r"Q\d{9}")


def notes_from(text):
    out, cur, buf = {}, None, []
    for line in text.splitlines():
        ids = QID.findall(line)
        if ids:
            if cur and buf:
                out.setdefault(cur, "\n".join(buf).strip())
            cur, buf = ids[0], [line.strip()]
        elif cur is not None and line.strip():
            buf.append(line.strip())
    if cur and buf:
        out.setdefault(cur, "\n".join(buf).strip())
    return {q: n[:1500] for q, n in out.items()}


def main(a):
    if not a:
        sys.exit(__doc__)
    require_data_folder()
    prefix = a[0]
    texts = []
    if len(a) > 1:
        texts = [(p.name, p.read_text(errors="replace")) for p in sorted(Path(a[1]).glob("places_*.txt"))]
    else:
        every = []
        watch.list_drive(watch.CONFIG["drive_folder_id"], every=every)
        for name, fid in every:
            if name.lower().startswith("places_") and name.lower().endswith(".txt"):
                texts.append((name, watch.download(fid).decode("utf-8", "replace")))
    notes = {}
    for name, t in texts:
        for q, n in notes_from(t).items():
            notes[q] = n                               # a later file (a redo) replaces an older note
    got, without = 0, []
    led = watch.ledger()
    for p in sorted(QUEUE.glob(f"{prefix}-*.json")):
        if led.get(p.stem, {}).get("state") == "delivered":
            continue                                   # built already: notes are no use any more
        d = json.loads(p.read_text())
        changed = False
        for it in d["items"]:
            if it["qid"] in notes:
                if it.get("picture_notes") != notes[it["qid"]]:
                    it["picture_notes"] = notes[it["qid"]]
                    changed = True
                got += 1
            elif not it.get("picture_notes"):
                without.append(it["qid"])
        if changed:
            p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(texts)} places file(s); {got} questions have picture notes"
          + (f"; without notes ({len(without)}): {' '.join(without[:40])}" + (" ..." if len(without) > 40 else "")
             if without else ""))


if __name__ == "__main__":
    main(sys.argv[1:])
