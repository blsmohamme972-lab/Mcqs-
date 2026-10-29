#!/usr/bin/env python3
"""Decode and check the ZIPs collected from the Kafu ZIP inbox (config.json zip_inbox_url).

Builder sessions upload each package ZIP as base64 text (MCARDS_<PKG>_r1.zip.b64.txt).
Download the assets first (Artifact action "read" with path = the asset id, one per call),
then run:

  python3 -I collect_zips.py IN_DIR OUT_DIR [ID=SHA256:SIZE ...]

IN_DIR   folder holding the downloaded base64 files (<id>.txt or *.b64.txt)
OUT_DIR  where each good ZIP goes, named MCARDS_<package_id>_r<rev>.zip from the ZIP's own manifest (ready for
         preflight.py zips and merge_zips.py; nothing else is left there). A file that fails stays as <id>.zip so it
         can be looked at.
ID=SHA256:SIZE  optional, from the "list" scope "assets" output: checks each
                downloaded file against the inbox's sha256 and byte size.

Exit code 0 only when every file matches, decodes, and passes zipfile.testzip().
"""
import base64
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    src, out = Path(argv[0]), Path(argv[1])
    out.mkdir(parents=True, exist_ok=True)
    expect = {}
    for a in argv[2:]:
        aid, _, rest = a.partition("=")
        sha, _, size = rest.partition(":")
        expect[aid] = (sha.lower(), int(size) if size else None)

    files = sorted(p for p in src.iterdir() if p.is_file() and p.suffix == ".txt")
    if not files:
        print(f"no .txt files in {src}")
        return 1
    bad = 0
    for p in files:
        aid = p.name.split(".")[0]
        raw = p.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        problems = []
        if aid in expect:
            want_sha, want_size = expect[aid]
            if sha != want_sha:
                problems.append(f"sha256 {sha} != {want_sha}")
            if want_size is not None and len(raw) != want_size:
                problems.append(f"size {len(raw)} != {want_size}")
        names = []
        try:
            data = base64.b64decode(b"".join(raw.split()), validate=True)
            zp = out / f"{aid}.zip"
            zp.write_bytes(data)
            with zipfile.ZipFile(zp) as z:
                broken = z.testzip()
                names = z.namelist()
                man = json.loads(z.read("motioncards-manifest.json")) if "motioncards-manifest.json" in names else None
            if broken is not None:
                problems.append(f"testzip: bad member {broken}")
            elif not man:
                problems.append("no motioncards-manifest.json")
            else:
                named = out / f"MCARDS_{man['package_id']}_r{man.get('package_revision', 1)}.zip"
                if named.exists() and named.read_bytes() != data:
                    problems.append(f"{named.name} already collected with different content (two builds of one package?)")
                else:
                    shutil.move(zp, named)                 # only the MCARDS_ name stays: merge_zips reads every MCARDS_*
                    names = [named.name, f"{len(man.get('animations', []))} lessons"]
        except Exception as e:  # bad base64 or not a zip
            problems.append(f"{type(e).__name__}: {e}")
        status = "OK" if not problems else "FAIL " + "; ".join(problems)
        print(f"{aid}  {len(raw)} B  sha256 {sha}  {status}  {names}")
        bad += bool(problems)
    missing = sorted(set(expect) - {p.name.split('.')[0] for p in files})
    for aid in missing:
        print(f"{aid}  FAIL not downloaded")
    print(f"{len(files) - bad}/{len(files)} ok" + (f", {len(missing)} missing" if missing else ""))
    return 1 if bad or missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
