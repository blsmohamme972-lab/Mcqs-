#!/usr/bin/env python3
"""The Google Drive folder that holds the images (one folder for everything, chosen by the owner).

  drive.py show          the folder in use: name, id, link, how many files it lists now
  drive.py set LINK      make this folder the one in use. LINK is the folder's share link
                         (https://drive.google.com/drive/folders/<id>?usp=sharing) or its id.
                         The folder must be shared "Anyone with the link"; its name is read from Drive.

`set` writes the choice to the run's data folder (<data>/config.local.json); nothing is written to GitHub. Then make the
master prompt again (gpt_writer.py --master): the painter cards carry the folder's link and name, so cards made before the
change still point at the old folder.
"""
import html
import json
import re
import sys
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import watch  # noqa: E402

from kafu_data import LOCAL_CONFIG, load_config  # noqa: E402


def folder_id(link):
    link = link.strip()
    for pat in (r"/folders/([\w-]{10,})", r"[?&]id=([\w-]{10,})"):
        m = re.search(pat, link)
        if m:
            return m.group(1)
    if re.fullmatch(r"[\w-]{10,}", link):
        return link
    sys.exit("FAIL: this is not a Drive folder link (expected .../drive/folders/<id>)")


def probe(fid):
    try:
        page = watch.fetch(f"https://drive.google.com/embeddedfolderview?id={fid}").decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        sys.exit(f"FAIL: Drive answered {e.code}. Share the folder as 'Anyone with the link' (Viewer) and send the link again.")
    m = re.search(r"<title>(.*?)</title>", page, re.S)
    name = html.unescape(m.group(1)).strip() if m else ""
    if not name or "flip-entries" not in page:
        sys.exit("FAIL: Drive did not show the folder. Share it as 'Anyone with the link' and send the link again.")
    every = []
    watch.list_drive(fid, every=every)
    return name, len(every)


def main(a):
    cfg = load_config()
    if not a or a[0] == "show":
        name, n = probe(cfg["drive_folder_id"])
        print(f'folder "{name}"  id {cfg["drive_folder_id"]}  files {n}\n{cfg["drive_folder_url"]}')
        return
    if a[0] != "set" or len(a) < 2:
        sys.exit(__doc__)
    fid = folder_id(a[1])
    name, n = probe(fid)
    if '"' in name:
        sys.exit("FAIL: rename the folder without double quotes")
    from kafu_data import require_data_folder
    require_data_folder()
    local = json.loads(LOCAL_CONFIG.read_text()) if LOCAL_CONFIG.exists() else {}
    local.update(drive_folder_id=fid, drive_folder_url=f"https://drive.google.com/drive/folders/{fid}", drive_folder_name=name)
    LOCAL_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_CONFIG.write_text(json.dumps(local, indent=2, ensure_ascii=False) + "\n")
    print(f'OK: images now go to folder "{name}" ({n} files in it now)\n{local["drive_folder_url"]}\n'
          f"Saved in {LOCAL_CONFIG}. Next: send the owner a new master prompt (gpt_writer.py --master).")


if __name__ == "__main__":
    main(sys.argv[1:])
