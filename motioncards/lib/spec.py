from __future__ import annotations
import re
PACKAGE_TYPE="kafu-motioncards"
SCHEMA_VERSION=1
RUNTIME_VERSION=1
PROTOCOL_VERSION=1
MANIFEST_NAME="motioncards-manifest.json"
MAX_ZIP_BYTES=19*1024*1024
MAX_EXPANDED_BYTES=80*1024*1024
MAX_ENTRIES=1200
MAX_RATIO=100.0
MIN_DURATION_MS=2000
MAX_DURATION_MS=180000          # image lessons run up to 3 minutes
MAX_ANIMATIONS=500
MAX_ENTRY_BYTES=2*1024*1024
QID_RE=re.compile(r"^Q\d{9}$")
PACKAGE_ID_RE=re.compile(r"^[A-Z0-9][A-Z0-9-]{0,63}$")
ZIP_NAME_RE=re.compile(r"^MCARDS_([A-Z0-9][A-Z0-9-]{0,63})_r([1-9]\d*)(?:_part([1-9]\d*)of([1-9]\d*))?\.zip$",re.I)
FORBIDDEN_BASENAMES={"_worker.js","_headers","_redirects","package.json","package-lock.json","pnpm-lock.yaml","yarn.lock"}
FORBIDDEN_EXTENSIONS={".exe",".dll",".so",".dylib",".sh",".bash",".bat",".cmd",".ps1",".py",".pyc",".mjs",".cjs",".wasm"}
PUBLIC_PREFIXES=("entries/","indexes/","voice/")
# Voice-over (voiceover/): one Ogg Opus track per card, embedded in the compiled entry and handed to the host.
VOICE_MIME="audio/ogg; codecs=opus"
MAX_VOICE_BYTES=640*1024        # 3 minutes at 24 kbps (Breeze 'medium') with room to spare
MAX_VOICE_CUES=64              # a dialogue lesson has one cue per spoken line
SOURCE_PREFIXES=("source/","scenes/","reports/")
ALLOWED_ROOT_FILES={MANIFEST_NAME,"validation-report.json"}

def parse_package_filename(name:str):
    if not isinstance(name,str) or len(name)>255:return None
    m=ZIP_NAME_RE.fullmatch(name)
    if not m:return None
    revision=int(m.group(2));part=int(m.group(3) or 1);total=int(m.group(4) or 1)
    if total>100 or part>total or (total==1 and m.group(3)):return None
    pid=m.group(1).upper()
    return {"package_id":pid,"package_revision":revision,"part":part,"total":total,"group_key":f"{pid}_r{revision}"}

def validate_duration(value):
    if not isinstance(value,int) or isinstance(value,bool) or not MIN_DURATION_MS<=value<=MAX_DURATION_MS:
        raise ValueError(f"duration_ms must be an integer in [{MIN_DURATION_MS},{MAX_DURATION_MS}]")
    return value
