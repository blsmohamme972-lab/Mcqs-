#!/usr/bin/env python3
"""Set up the Breeze voice engine so that it cannot fail on a cut download (builder sessions; autobuild.py runs it).

  python3 voice_setup.py [REPO]        REPO = the Mcqs- checkout (default: the current directory)

Why: the repository's own downloader (voiceover.py download_resuming) returns as soon as a transfer ends, even when the
connection was cut silently; the SHA-256 check then fails ("SHA-256 mismatch ... refusing to use it"), the partial file is
deleted and the next try starts again from zero (3.5 GB). That was the "Breeze SHA" failure of the earlier runs.
Here every pinned file is fetched first with a size-checked, resuming download (each piece must continue exactly where the
last stopped), verified with its SHA-256 and put where voiceover.py looks for it, so its own setup finds it and skips the
download. Then the normal setup runs (LESSON_PROMPT step 1) and a 4-second Breeze test clip proves the engine works.
Prints "VOICE OK" or "VOICE BROKEN: <reason>" as the last line (exit code 0 / 1).
"""
import ast
import hashlib
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
CACHE = Path.home() / ".cache" / "kafu-voiceover"
VPY = Path.home() / ".venvs" / "kafu-voice" / "bin" / "python"


def pinned(repo):
    """{target path: (url, sha256)} read from voiceover.py itself, so a new pin in the repository is followed."""
    tree = ast.parse((repo / "voiceover" / "voiceover.py").read_text())
    vals = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and getattr(node.targets[0], "id", "") in ("MODEL", "BREEZE"):
            vals[node.targets[0].id] = ast.literal_eval(node.value)
    out = {CACHE / name: tuple(v) for name, v in vals["MODEL"].items()}
    out[CACHE / "breeze" / Path(vals["BREEZE"]["model"][0]).name] = tuple(vals["BREEZE"]["model"])
    return out


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def fetch(url, digest, target, tries=40):
    if target.exists() and sha256(target) == digest:
        print(f"ok {target.name} (already there)", flush=True)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + ".kafu-part")
    total = None
    for attempt in range(1, tries + 1):
        have = part.stat().st_size if part.exists() else 0
        if total is not None and have == total:
            break
        req = urllib.request.Request(url, headers={"Range": f"bytes={have}-", "User-Agent": "kafu-voice-setup"})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                cr = r.headers.get("Content-Range", "")          # "bytes START-END/TOTAL"
                if r.status == 206 and cr.startswith("bytes ") and "/" in cr:
                    start = int(cr.split()[1].split("-")[0])
                    total = int(cr.split("/")[1])
                    if start != have:                           # a piece that does not continue exactly: start over
                        part.unlink(missing_ok=True)
                        continue
                    mode = "ab"
                else:                                           # the server sent the whole file
                    total = int(r.headers.get("Content-Length") or 0) or None
                    mode = "wb"
                with open(part, mode) as f:
                    while True:
                        b = r.read(1 << 22)
                        if not b:
                            break
                        f.write(b)
        except (OSError, urllib.error.URLError) as e:
            print(f"  {target.name}: interrupted at {part.stat().st_size if part.exists() else 0} bytes ({type(e).__name__}); "
                  f"resuming ({attempt}/{tries})", flush=True)
            time.sleep(min(30, 2 * attempt))
            continue
        have = part.stat().st_size
        if total is None or have >= total:
            break
        print(f"  {target.name}: transfer ended early at {have}/{total} bytes; resuming ({attempt}/{tries})", flush=True)
    got = sha256(part)
    if got != digest:
        part.unlink(missing_ok=True)
        raise SystemExit(f"VOICE BROKEN: {target.name} SHA-256 {got[:12]} after a complete download; the pinned file changed upstream")
    os.replace(part, target)
    print(f"ok {target.name} {digest[:12]}", flush=True)


def run(cmd, repo, env, log_tail=12):
    r = subprocess.run(cmd, cwd=repo, env=env, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip().splitlines()
    for line in out[-log_tail:]:
        print("  " + line[:300], flush=True)
    return r.returncode, "\n".join(out)


def preload_recogniser(repo, env):
    """The word highlight uses faster-whisper base.en; load it now (3 tries) so a lesson build never meets a cut download.
    Not fatal: without it the lessons fall back to length-based word timing."""
    code_txt = "from faster_whisper import WhisperModel; WhisperModel('base.en', device='cpu', compute_type='int8'); print('ASR OK')"
    for attempt in (1, 2, 3):
        r = subprocess.run([str(VPY), "-c", code_txt], cwd=repo, env=env, capture_output=True, text=True)
        if "ASR OK" in r.stdout:
            print("ok word-timing model (faster-whisper base.en)", flush=True)
            return True
        time.sleep(10 * attempt)
    print("note: the word-timing model did not load; lessons will use length-based word timing", flush=True)
    return False


def detach_if_environment_setup():
    """The cloud environment's setup script is killed after about 5 minutes (exit code -1), and the Breeze download takes
    longer. Outside Claude Code (no CLAUDECODE variable: the setup script runs before it starts) the setup therefore goes on
    in the background, detached, writing to the same log; the worker waits for "VOICE OK" there."""
    if os.environ.get("CLAUDECODE") or os.environ.get("KAFU_SETUP_DETACHED"):
        return False
    if os.fork():
        print("setup continues in the background (environment setup script)", flush=True)
        return True
    os.setsid()
    if os.fork():
        os._exit(0)
    os.environ["KAFU_SETUP_DETACHED"] = "1"
    return False


def main():
    if detach_if_environment_setup():
        return 0
    repo = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    env = {**os.environ, "MOTIONCARDS_CHROMIUM": CHROME}
    for target, (url, digest) in pinned(repo).items():
        fetch(url, digest, target)
    steps = [["pip", "install", "-q", "playwright"], ["bash", "voiceover/bootstrap.sh"],
             [str(VPY), "voiceover/voiceover.py", "setup", "--engine", "breeze"]]
    for attempt in (1, 2):
        ok = True
        for cmd in steps:
            code, out = run(cmd, repo, env)
            if code:
                print(f"step failed: {' '.join(cmd[:3])} (exit {code})", flush=True)
                ok = False
                break
        if ok:
            code, out = run([str(VPY), "voiceover/voiceover.py", "sample", "--engines", "breeze", "--seconds", "4",
                             "--out", "work/voice-smoke"], repo, env)
            if code == 0 and "Breeze_4s.mp3" in out:
                preload_recogniser(repo, env)
                print("VOICE OK", flush=True)
                return 0
            print("voice test clip failed", flush=True)
        if attempt == 1:
            print("retrying the setup once", flush=True)
    print("VOICE BROKEN: the setup or the 4-second Breeze test failed twice (see the lines above)", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
