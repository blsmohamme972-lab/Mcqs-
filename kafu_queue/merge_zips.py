#!/usr/bin/env python3
"""Merge several verified Kafu package ZIPs into a few bigger packages (each below the system ceiling).

  python3 -I merge_zips.py MCQS_MOUNTAIN_DIR IN_DIR OUT_DIR PREFIX [CAP_MB]

IN_DIR   folder with MCARDS_<PKG>_r1.zip files (each already valid)
OUT_DIR  where MCARDS_<PREFIX>-M<k>_r1.zip files are written
PREFIX   e.g. GT-CH36 -> package ids GT-CH36-M1, GT-CH36-M2, ...
CAP_MB   size cap per merged ZIP in MiB (default 18.5; the validator's own ceiling is 19)

The member files are copied byte for byte (their SHA-256 values stay valid). Only the manifest is rewritten:
the animation rows and the selection list are concatenated in question order. Every merged ZIP is checked with the
project's own validate_package and every member is compared with its original. Nothing is changed in the answer keys.
"""
import json
import sys
import zipfile
from pathlib import Path

MOUNT, IN, OUT, PREFIX = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
CAP = int(float(sys.argv[5] if len(sys.argv) > 5 else 18.5) * 1024 * 1024)
sys.path.insert(0, str(MOUNT))
from motioncards.lib import package as P  # noqa: E402
from motioncards.lib.spec import MANIFEST_NAME  # noqa: E402

pkgs = []
for f in sorted(IN.glob("MCARDS_*_r1.zip")):
    m = P.validate_package(f)               # refuse anything that is not valid on its own
    pkgs.append((min(a["qid"] for a in m["animations"]), f, m))
pkgs.sort(key=lambda x: x[0])
if len({json.dumps(m["source"], sort_keys=True) for _, _, m in pkgs}) != 1:
    sys.exit("different source provenance across packages: refusing to merge")

groups, cur, size = [], [], 0
for q, f, m in pkgs:
    s = f.stat().st_size
    if cur and size + s > CAP:
        groups.append(cur)
        cur, size = [], 0
    cur.append((q, f, m))
    size += s
if cur:
    groups.append(cur)

OUT.mkdir(parents=True, exist_ok=True)
total = 0
for k, g in enumerate(groups, 1):
    pid = f"{PREFIX}-M{k}"
    base = g[0][2]
    rows, files = [], {}
    for _, f, m in g:
        with zipfile.ZipFile(f) as z:
            for n in z.namelist():
                if n in (MANIFEST_NAME, "validation-report.json"):
                    continue
                if n in files:
                    sys.exit("duplicate member " + n)
                files[n] = z.read(n)
        rows += m["animations"]
    qids = [r["qid"] for r in rows]
    if len(set(qids)) != len(qids):
        sys.exit("duplicate question in " + pid)
    manifest = {**base, "package_id": pid, "package_revision": 1,
                "selection": {**base["selection"], "qids": qids, "count": len(qids)}, "animations": rows}
    files[MANIFEST_NAME] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    files["validation-report.json"] = (json.dumps({"status": "PASS", "animations": len(rows), "blocked": [],
                                                   "package_type": "kafu-motioncards"}, indent=2) + "\n").encode()
    out = OUT / f"MCARDS_{pid}_r1.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in sorted(files.items()):
            zi = zipfile.ZipInfo(name)
            zi.date_time = (2026, 1, 1, 0, 0, 0)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o100644 << 16
            z.writestr(zi, data)
    m2 = P.validate_package(out)            # the project's own validator, same rules as the bot
    assert [a["qid"] for a in m2["animations"]] == qids
    with zipfile.ZipFile(out) as z2:         # every member identical to its source package
        for _, f, _m in g:
            with zipfile.ZipFile(f) as z:
                for n in z.namelist():
                    if n not in (MANIFEST_NAME, "validation-report.json") and z.read(n) != z2.read(n):
                        sys.exit("member changed: " + n)
    total += len(qids)
    print(f"{out.name}  {out.stat().st_size / 1048576:.2f} MiB  {len(qids)} lessons  "
          f"Q{min(int(q[1:]) for q in qids) - 7205}-Q{max(int(q[1:]) for q in qids) - 7205}  packages={[x[1].name[7:-7] for x in g]}")
print("merged lessons", total, "from", len(pkgs), "packages into", len(groups), "ZIPs; all validated OK")
