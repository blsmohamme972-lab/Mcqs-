#!/usr/bin/env python3
"""A run's data travels in one file through the owner's inbox, never through GitHub (owner's rule).

  bundle.py use DIR                 Head: make DIR the data folder of this session (writes ~/.kafu_data). Put it in the
                                    scratchpad, never inside the repository.
  bundle.py pack OUT.json           Head: everything a builder needs in one file: the exports, the packages, the voice
                                    scripts, the ledger and the owner's settings (config.local.json), with a check code.
                                    Upload it to the inbox as an asset (Artifact publish, asset true) and give its asset id
                                    to assign.py prompt ... --bundle <id>.
  bundle.py unpack FILE DIR         Builder: check the file and unpack it into DIR, then use DIR as the data folder.
  bundle.py where                   print the data folder in use
"""
import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kafu_data as K  # noqa: E402


def code(d):
    return hashlib.sha256(json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()[:16]


def use(d):
    d = Path(d).resolve()
    for sub in ("queue", "voice", "exports"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    K.POINTER.parent.mkdir(parents=True, exist_ok=True)
    K.POINTER.write_text(str(d) + "\n")
    print(f"data folder: {d}")


def pack(out):
    D = K.data_dir()
    if D.resolve() == K.HERE.resolve():
        sys.exit("no data folder set: run bundle.py use <scratchpad>/kafu-data first")
    rd = lambda p: json.loads(p.read_text())  # noqa: E731
    b = {"format": "kafu-bundle-v1", "made": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
         "exports": {p.name: p.read_text() for p in sorted((D / "exports").glob("*.json"))},
         "packages": {p.stem: rd(p) for p in sorted((D / "queue").glob("*.json"))},
         "voice": {p.stem: rd(p) for p in sorted((D / "voice").glob("Q*.json"))},
         "ledger": rd(D / "ledger.json") if (D / "ledger.json").exists() else {},
         "config_local": rd(D / "config.local.json") if (D / "config.local.json").exists() else {}}
    need = {Path(q["export"]).name for q in b["packages"].values()}
    if need - set(b["exports"]):
        sys.exit(f"exports missing from the data folder: {sorted(need - set(b['exports']))}")
    b["check"] = code(b)
    Path(out).write_text(json.dumps(b, ensure_ascii=True))
    print(f"{out}: {len(b['packages'])} packages, {len(b['exports'])} exports, {len(b['voice'])} voice scripts, "
          f"{Path(out).stat().st_size} bytes, check {b['check']}")


def unpack(f, d):
    raw = Path(f).read_text(encoding="utf-8")
    a, z = raw.find("{"), raw.rfind("}")
    b = json.loads(raw[a:z + 1])
    if b.get("format") != "kafu-bundle-v1":
        sys.exit("FAIL: not a Kafu bundle")
    chk = b.pop("check", None)
    if code(b) != chk:
        sys.exit("FAIL: bundle check code does not match (the file changed on the way); ask the Head for it again")
    d = Path(d)
    use(d)
    for name, text in b["exports"].items():
        (d / "exports" / name).write_text(text)
    for name, q in b["packages"].items():
        (d / "queue" / f"{name}.json").write_text(json.dumps(q, indent=1, ensure_ascii=False) + "\n")
    for name, v in b["voice"].items():
        (d / "voice" / f"{name}.json").write_text(json.dumps(v, indent=1, ensure_ascii=False) + "\n")
    (d / "ledger.json").write_text(json.dumps(b["ledger"], indent=1) + "\n")
    if b["config_local"]:
        (d / "config.local.json").write_text(json.dumps(b["config_local"], indent=2) + "\n")
    print(f"BUNDLE OK: {len(b['packages'])} packages, {len(b['exports'])} exports, {len(b['voice'])} voice scripts (made {b['made']})")


def main(a):
    if not a:
        sys.exit(__doc__)
    if a[0] == "use" and len(a) == 2:
        use(a[1])
    elif a[0] == "pack" and len(a) == 2:
        pack(a[1])
    elif a[0] == "unpack" and len(a) == 3:
        unpack(a[1], a[2])
    elif a[0] == "where":
        print(K.data_dir())
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
