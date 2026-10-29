#!/usr/bin/env python3
"""Head: put a worker's recordings into this machine's Breeze cache.

  python3 -I import_voice.py PARTS_DIR [CACHE_DIR]    PARTS_DIR = a NEW folder with that slot's voice_<slot>_NN.b64.txt files

Decodes the parts in order, checks the tar against DONE sha (if DONE.txt is there), refuses unsafe names, converts each FLAC
back to the WAV under its cache name (breeze/lines/<name>.wav) and the voice references to breeze/voices/. A line that is
already cached is kept. Prints "IMPORT OK <n> lines" or the problem.
"""
import base64
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
from pathlib import Path

src = Path(sys.argv[1])
cache = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.home() / ".cache" / "kafu-voiceover"
parts = sorted(src.glob("voice_*_*.b64.txt"))
if not parts:
    sys.exit("IMPORT FAILED: no voice_*.b64.txt parts")
data = b"".join(base64.b64decode(p.read_text().strip()) for p in parts)
done = next(iter(sorted(src.glob("DONE*.txt"))), None)
if done is not None:
    want = json.loads(done.read_text()).get("tar_sha256")
    if want and hashlib.sha256(data).hexdigest() != want:
        sys.exit("IMPORT FAILED: tar checksum differs (a part is cut or missing)")
t = tarfile.open(fileobj=io.BytesIO(data))
man = json.loads(t.extractfile("manifest.json").read())
SAFE = re.compile(r"^[0-9a-zA-Z_.\-]+$")
n = 0
for m in t.getmembers():
    if not m.isfile() or m.name == "manifest.json":
        continue
    kind, name = m.name.split("/", 1)
    if kind not in ("flac", "refs") or not SAFE.match(name):
        sys.exit(f"IMPORT FAILED: unexpected member {m.name}")
    mine = next((x for x in man["lines"] if x["flac"] == name), None) if kind == "flac" else None
    if kind == "flac" and not mine:
        continue
    raw = t.extractfile(m).read()
    if mine and hashlib.sha256(raw).hexdigest() != mine["sha256"]:
        sys.exit(f"IMPORT FAILED: {name} checksum differs")
    dest = cache / "breeze" / ("lines" if kind == "flac" else "voices") / (mine["cache_name"] if mine else name.rsplit(".", 1)[0] + ".wav")
    if dest.exists():
        continue
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part.wav")
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "flac", "-i", "pipe:0", "-ar", "24000", "-ac", "1", str(tmp)],
                       input=raw, capture_output=True)
    if r.returncode:
        sys.exit("IMPORT FAILED: ffmpeg " + r.stderr.decode()[-200:])
    tmp.replace(dest)
    n += kind == "flac"
print(f"IMPORT OK {n} lines (manifest {len(man['lines'])}, failed {man['failed']})")
