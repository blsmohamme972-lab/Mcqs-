"""Validate a content folder and zip it into an importable package.

The folder holds manifest.json plus the media it references (see docs/package-format.md).
Validation mirrors the app's importer, so a zip that passes here imports cleanly.

Usage: python3 tools/build_package.py content/<package-id> dist/<package-id>.zip
"""
import json
import os
import re
import sys
import zipfile

ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
TYPES = {"basic", "occlusion", "mcq"}
SKIP = {".py", ".pyc"}


def validate_lecture(s, root):
    """Mirror of SceneDef.lectureErrors in the app (pkg/Lecture.kt)."""
    lec = s.get("lecture")
    if lec is None:
        return []
    who = f"scene {s['id']} lecture"
    errors = []
    if not s.get("image"):
        errors.append(f"{who}: needs the scene image")
    if lec.get("audio") and not os.path.isfile(os.path.join(root, lec["audio"])):
        errors.append(f"{who}: missing file {lec['audio']!r}")
    if lec.get("duration") is not None and lec["duration"] <= 0:
        errors.append(f"{who}: duration must be > 0")
    ids = {r["id"] for r in s.get("regions", [])}
    hidden = lec.get("hidden", [])
    errors += [f"{who}: unknown hidden region {h!r}" for h in hidden if h not in ids]
    last = 0.0
    for i, c in enumerate(lec.get("cues", [])):
        if c["at"] < last:
            errors.append(f"{who}: cue {i} is before the previous cue")
        last = max(last, c["at"])
        if c.get("focus") is not None and c["focus"] not in ids:
            errors.append(f"{who}: cue {i} unknown focus region {c['focus']!r}")
        errors += [f"{who}: cue {i} reveals {r!r} which is not hidden" for r in c.get("reveal", []) if r not in hidden]
        if c.get("zoom") is not None and c["zoom"] <= 0:
            errors.append(f"{who}: cue {i} zoom must be > 0")
        if c.get("camera") is not None and c["camera"].get("zoom", 1.0) <= 0:
            errors.append(f"{who}: cue {i} camera zoom must be > 0")
        if c.get("effect") not in (None, "pulse"):
            errors.append(f"{who}: cue {i} unknown effect {c['effect']!r}")
    return errors


def validate(m, root):
    errors = []
    if m.get("format") != 1:
        errors.append(f"unsupported format {m.get('format')}")
    if not ID_RE.match(m.get("id", "")):
        errors.append(f"invalid package id {m.get('id')!r}")
    if not m.get("title", "").strip():
        errors.append("empty title")

    def media(owner, path):
        if path is not None and not os.path.isfile(os.path.join(root, path)):
            errors.append(f"{owner}: missing file {path!r}")

    scenes = {}
    for s in m.get("scenes", []):
        if not ID_RE.match(s["id"]):
            errors.append(f"invalid scene id {s['id']!r}")
        if s["id"] in scenes:
            errors.append(f"duplicate scene id {s['id']!r}")
        scenes[s["id"]] = s
        media(f"scene {s['id']}", s.get("image"))
        media(f"scene {s['id']}", s.get("video"))
        errors += validate_lecture(s, root)
        seen = set()
        for r in s.get("regions", []):
            if r["id"] in seen:
                errors.append(f"scene {s['id']}: duplicate region {r['id']!r}")
            seen.add(r["id"])
            ok = r["x"] >= 0 and r["y"] >= 0 and r["w"] > 0 and r["h"] > 0 \
                and r["x"] + r["w"] <= 1.0001 and r["y"] + r["h"] <= 1.0001
            if not ok:
                errors.append(f"scene {s['id']}: region {r['id']!r} outside 0..1")

    ids = set()
    for c in m.get("cards", []):
        who = f"card {c.get('id')}"
        if not ID_RE.match(c.get("id", "")):
            errors.append(f"invalid card id {c.get('id')!r}")
        if c.get("id") in ids:
            errors.append(f"duplicate card id {c.get('id')!r}")
        ids.add(c.get("id"))
        t = c.get("type")
        if t not in TYPES:
            errors.append(f"{who}: unknown type {t!r}")
        if not c.get("front", "").strip():
            errors.append(f"{who}: empty front")
        media(who, c.get("image"))
        if t in ("basic", "occlusion") and not (c.get("back") or "").strip():
            errors.append(f"{who}: {t} card needs back")
        if t == "occlusion":
            s = scenes.get(c.get("scene"))
            if s is None:
                errors.append(f"{who}: unknown scene {c.get('scene')!r}")
            elif not s.get("image"):
                errors.append(f"{who}: scene {s['id']!r} has no image")
            elif c.get("region") not in {r["id"] for r in s.get("regions", [])}:
                errors.append(f"{who}: unknown region {c.get('region')!r}")
        if t == "mcq":
            opts = c.get("options", [])
            if len(opts) < 2:
                errors.append(f"{who}: mcq needs at least 2 options")
            if not isinstance(c.get("answer"), int) or not 0 <= c["answer"] < len(opts):
                errors.append(f"{who}: mcq answer index invalid")
        if t != "occlusion" and c.get("scene") is not None and c["scene"] not in scenes:
            errors.append(f"{who}: unknown scene {c['scene']!r}")
    return errors


def main(src, out):
    with open(os.path.join(src, "manifest.json"), encoding="utf-8") as f:
        m = json.load(f)
    errors = validate(m, src)
    if errors:
        print("INVALID:\n  " + "\n  ".join(errors))
        sys.exit(1)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    entries = []
    for dirpath, dirs, files in os.walk(src):
        dirs.sort()
        for name in sorted(files):
            if os.path.splitext(name)[1] in SKIP or name.startswith("."):
                continue
            full = os.path.join(dirpath, name)
            entries.append((os.path.relpath(full, src).replace(os.sep, "/"), full))
    # Deterministic zip (fixed timestamps, sorted entries): unchanged content -> identical sha256,
    # so the app only downloads packages that really changed.
    with zipfile.ZipFile(out, "w") as z:
        for rel, full in sorted(entries):
            info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            # Media is already compressed; store it to keep import fast.
            info.compress_type = zipfile.ZIP_DEFLATED if rel.endswith(".json") else zipfile.ZIP_STORED
            with open(full, "rb") as f:
                z.writestr(info, f.read())
    print(f"OK {m['id']} v{m.get('version', 1)}: {len(m['cards'])} cards, "
          f"{len(m.get('scenes', []))} scenes -> {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
