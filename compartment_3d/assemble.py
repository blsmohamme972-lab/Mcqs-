"""Inline the packed model into the page: build/leg.bin + build/leg_meta.json -> compartment_3d.html.

Usage: python assemble.py [mp4_bytes]
"""
import base64
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
mp4 = int(sys.argv[1]) if len(sys.argv) > 1 else 0
src = open(os.path.join(HERE, "compartment_3d.src.html"), encoding="utf-8").read()
blob = open(os.path.join(HERE, "build", "leg.bin"), "rb").read()
meta = json.load(open(os.path.join(HERE, "build", "leg_meta.json")))
tris = sum(p["ni"] for p in meta["parts"]) // 3
out = (src.replace("__META__", json.dumps(meta, separators=(",", ":")))
          .replace("__BIN__", base64.b64encode(blob).decode())
          .replace("__MP4_BYTES__", str(mp4))
          .replace("__MP4_SIZE__", f"{mp4 / 1e6:.1f} MB" if mp4 else "–")
          .replace("__TRIS__", f"{tris:,}")
          .replace("__MODEL_KB__", str(round(len(blob) / 1024))))
path = os.path.join(HERE, "compartment_3d.html")
open(path, "w", encoding="utf-8").write(out)
print(path, len(out.encode()), "bytes")
