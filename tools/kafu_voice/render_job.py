#!/usr/bin/env python3
"""Voice worker: render every line of a job file with Breeze and pack the recordings (run from the Mcqs- checkout).

  <voice python> render_job.py JOB.json OUTDIR SLOT ROUND

JOB.json = {"slot": "11", "round": 1, "final": false, "lines": [{"id": "Q000000234-01", "voice": "lecturer-woman", "dir": "calm", "text": "..."}]}
Every line goes through the repository's own breeze_text + breeze_wav (cached by key, so a run that is stopped resumes by
itself). At the end OUTDIR holds voice_<slot>_r<round>_NN.b64.txt parts (base64 of a tar of the FLAC recordings +
manifest.json, at most 6 MB each) and DONE_<slot>_r<round>.txt. Prints one status line per step and "RENDER DONE n/m" last.
"""
import base64
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import time
from pathlib import Path

repo = Path.cwd()
sys.path.insert(0, str(repo / "voiceover"))
import voiceover as v  # noqa: E402

job = json.loads(Path(sys.argv[1]).read_text())
out = Path(sys.argv[2])
slot = sys.argv[3] if len(sys.argv) > 3 else str(job.get("slot", "00"))
rnd = sys.argv[4] if len(sys.argv) > 4 else str(job.get("round", 1))
tag = f"{slot}_r{rnd}"
out.mkdir(parents=True, exist_ok=True)
(out / "flac").mkdir(exist_ok=True)
if os.environ.get("KAFU_STUB"):                       # test without Breeze: a tone per line
    def stub(text, voice, direction=None):
        p = out / ("stub_" + hashlib.sha256(f"{text}|{voice}|{direction}".encode()).hexdigest()[:16] + ".wav")
        if not p.exists():
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency=330:duration={0.4 + len(text) / 40:.2f}",
                            "-ar", "24000", "-ac", "1", str(p)], check=True)
        return p
    v.breeze_wav = stub
if not os.environ.get("KAFU_STUB") and not v.breeze_paths()[0].exists():
    print("building the portable Breeze binary first (a few minutes)", flush=True)
    v.setup_breeze()                                  # same process as the render: no separate command to approve
lex = v.load_lexicon()
manifest, failed = [], []
t0 = time.time()
for n, L in enumerate(job["lines"], 1):
    text, voice, direction = v.breeze_text(L["text"], lex), L["voice"], (L.get("dir") or None)
    for attempt in (1, 2):
        try:
            wav = v.breeze_wav(text, voice, direction)
            break
        except Exception as e:  # noqa: BLE001
            wav = None
            print(f"line {L['id']} attempt {attempt} failed: {str(e)[-200:]}", flush=True)
    if wav is None:
        failed.append(L["id"])
        continue
    fl = out / "flac" / (wav.stem + ".flac")
    if not fl.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-c:a", "flac", str(fl)], check=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(fl)],
                               capture_output=True, text=True).stdout.strip() or 0)
    if dur < 0.3:
        failed.append(L["id"])
        print(f"line {L['id']} is too short ({dur:.2f}s)", flush=True)
        continue
    manifest.append({"id": L["id"], "cache_name": wav.name, "flac": fl.name, "seconds": round(dur, 2), "voice": voice,
                     "dir": direction, "text": text, "sha256": hashlib.sha256(fl.read_bytes()).hexdigest()})
    print(f"line {n}/{len(job['lines'])} {L['id']} {dur:.1f}s ({time.time() - t0:.0f}s elapsed)", flush=True)
(out / "manifest.json").write_text(json.dumps({"slot": slot, "lines": manifest, "failed": failed}, indent=1))
# the designed-voice reference recordings the lines were cloned from (the Head's cache needs them under the same names)
refs = out / "refs"
refs.mkdir(exist_ok=True)
for w in sorted((v.CACHE / "breeze" / "voices").glob("*.wav")):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(w), "-c:a", "flac", str(refs / (w.stem + ".flac"))], check=True)
tar = out / f"voice_{tag}.tar"
with tarfile.open(tar, "w") as t:
    t.add(out / "manifest.json", "manifest.json")
    for f in sorted((out / "flac").glob("*.flac")):
        if f.name in {m["flac"] for m in manifest}:
            t.add(f, "flac/" + f.name)
    for f in sorted(refs.glob("*.flac")):
        t.add(f, "refs/" + f.name)
data, part = tar.read_bytes(), 4_500_000                 # base64 makes it a third bigger: 6 MB per text part
n, shas = 0, []
for i in range(0, len(data), part):
    n += 1
    txt = base64.b64encode(data[i:i + part]).decode()
    (out / f"voice_{tag}_{n:02d}.b64.txt").write_text(txt)
    shas.append(hashlib.sha256(txt.encode()).hexdigest())
(out / f"DONE_{tag}.txt").write_text(json.dumps({"slot": slot, "round": rnd, "parts": n, "part_sha256": shas, "lines": len(manifest),
                                                 "failed": failed, "tar_sha256": hashlib.sha256(data).hexdigest()}))
(out / "index.html").write_text(f"<title>Kafu voice {tag}</title><p>Voice recordings for the Head: slot {slot}, round {rnd}, "
                                 f"{n} part(s). Files: " + ", ".join([f"voice_{tag}_{i:02d}.b64.txt" for i in range(1, n + 1)] + [f"DONE_{tag}.txt"]))
print(f"parts {n}, tar sha256 {hashlib.sha256(data).hexdigest()}")
print(f"RENDER DONE {len(manifest)}/{len(job['lines'])}" + (f" FAILED {failed}" if failed else ""))
sys.exit(1 if failed else 0)
