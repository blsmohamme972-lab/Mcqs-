"""Write index.json for a release: the app reads it to find new content packages and app updates.

Usage: python3 tools/make_index.py <dist-dir> <base-url> <version-code> <version-name>
  <base-url> is where the release assets live, e.g.
  https://github.com/OWNER/REPO/releases/download/v0.2.7
"""
import datetime
import hashlib
import json
import os
import sys
import zipfile


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(dist, base, version_code, version_name):
    packages = []
    for name in sorted(os.listdir(dist)):
        if not name.endswith(".zip"):
            continue
        path = os.path.join(dist, name)
        with zipfile.ZipFile(path) as z:
            m = json.loads(z.read("manifest.json"))
        packages.append({
            "id": m["id"], "title": m["title"], "version": m.get("version", 1),
            "url": f"{base}/{name}", "sha256": sha256(path), "size": os.path.getsize(path),
        })
    index = {
        "format": 1,
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "app": {
            "versionCode": int(version_code), "versionName": version_name,
            "url": f"{base}/MCQs.apk", "sha256": sha256(os.path.join(dist, "MCQs.apk")),
        },
        "packages": packages,
    }
    with open(os.path.join(dist, "index.json"), "w") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(json.dumps(index, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:5])
