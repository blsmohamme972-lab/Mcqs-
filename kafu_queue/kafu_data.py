"""Where a run keeps its data. Nothing of a run is written to GitHub (owner's rule): the packages, the ledger, the voice
scripts, the exports, the slot split and any setting the owner changes (the Drive folder) live in one data folder.

The data folder is, in this order: $KAFU_DATA, the path written in ~/.kafu_data (bundle.py use / unpack writes it), or this
code folder itself (only for tests and old runs). config.json in this folder holds the defaults; <data>/config.local.json
overrides them (drive.py set writes it).
"""
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
POINTER = Path.home() / ".kafu_data"


def data_dir():
    if os.environ.get("KAFU_DATA"):
        return Path(os.environ["KAFU_DATA"])
    if POINTER.exists() and POINTER.read_text().strip():
        return Path(POINTER.read_text().strip())
    return HERE


DATA = data_dir()
QUEUE = Path(os.environ.get("KAFU_QUEUE_DIR", DATA / "queue"))
LEDGER = Path(os.environ.get("KAFU_LEDGER", DATA / "ledger.json"))
VOICE = DATA / "voice"
EXPORTS = DATA / "exports"
ASSIGN = DATA / "assignments.json"
LOCAL_CONFIG = DATA / "config.local.json"


def load_config():
    cfg = json.loads((HERE / "config.json").read_text())
    if LOCAL_CONFIG.exists():
        cfg.update(json.loads(LOCAL_CONFIG.read_text()))
    return cfg


CONFIG = load_config()


def require_data_folder():
    """Writers call this first: a run's data must never land inside the repository (nothing goes to GitHub)."""
    import sys
    if DATA.resolve() == HERE.resolve() and not os.environ.get("KAFU_ALLOW_REPO_DATA"):
        sys.exit("STOP: no data folder set. Run: python3 kafu_queue/bundle.py use <scratchpad>/kafu-data "
                 "(the run's data never goes into the repository)")


def export_path(name):
    """A package's export: its file name in the data folder's exports/ (older packages stored 'exports/<name>')."""
    return EXPORTS / Path(name).name
