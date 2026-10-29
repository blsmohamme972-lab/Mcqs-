#!/usr/bin/env python3
"""Kafu MotionCards voice-over: free, offline, small, synced narration for MotionCards.

Agent quick start (Golden rule 8):  voiceover/bootstrap.sh  then  voiceover.py make --engine <kokoro|elevenlabs> --workspace work/<batch>
ASK THE OWNER which engine first (kokoro = free, offline; elevenlabs = paid API, needs ELEVENLABS_API_KEY). `make` refuses to
guess. `sample` makes a short test clip from each engine so the owner can listen before choosing.

Pipeline (one command per step):
  make    everything below in one go (setup if needed, draft, synth, check, review), then ONE list of every problem
  setup   download the pinned Kokoro-82M model + voices (Apache-2.0), check SHA-256, find a Chromium for review videos
  draft   write work/<batch>/voice/<QID>.voice.json, lines pre-filled from the scene's numbered captions
          (re-times kept scripts when the captions move; guesses beats for scenes without numbered captions)
  synth   speak each beat, fit it inside its beat window, place it on the card timeline,
          loudness-normalise, encode Opus 16 kbps mono -> work/<batch>/voice/<QID>.opus + .track.json
  check   listen back with a speech recogniser: every word understood, no stray sound, every beat starts on time
  review  render the card and mux it with its voice into work/<batch>/voice/review/<QID>.mp4
  sample  speak one test line with each chosen engine -> <out>/<Engine>_<N>s.mp3 (same loudness, same length) for the owner to compare

Run with the voice-over venv:  ~/.venvs/kafu-voice/bin/python voiceover/voiceover.py make --engine <kokoro|elevenlabs> --workspace work/<batch>
See voiceover/README.md (the Golden 8 Rules) and voiceover/DESIGN.md.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, re, shutil, subprocess, sys, urllib.error, urllib.request
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CACHE = Path.home() / ".cache" / "kafu-voiceover"
CHROMIUM_FILE = CACHE / "chromium"   # written by `setup`: the Chromium review videos and the browser test use
SR = 24000                      # Kokoro output rate; Opus encodes it natively (super-wideband)
BITRATE = "16k"                 # Golden rule 1: chosen by listening test + ASR check (see DESIGN.md)
SMALL_BITRATE = "12k"           # only when 16 kbps would break the size budget (DESIGN.md §2: every word still understood)
MAX_SPEED = 1.2                 # never speed a voice up more than this to fit a beat
LEAD_MS, FIRST_LEAD_MS, TAIL_MS, END_HOLD_MS = 120, 250, 120, 350
MIN_WINDOW_MS = 500             # a beat shorter than this cannot hold even one spoken word
MAX_VOICE_BYTES = 20 * 1024     # Golden rule 5: at most 20 KB more per card download (an 8 s card is ~13 KB at 16 kbps)
# Owner's "high" quality (asked for after hearing 16 kbps ElevenLabs): full-band Opus at 48 kbps in music mode, about 42 KB
# for a 7 s card. Still inside the package validator's 64 KB per-card voice limit (motioncards/lib/spec.py).
QUALITY = {"standard": {"bitrate": BITRATE, "small": SMALL_BITRATE, "app": "voip", "frame": "60", "max": MAX_VOICE_BYTES},
           "medium": {"bitrate": "24k", "small": "20k", "app": "audio", "frame": "20", "max": 64 * 1024},
           "high": {"bitrate": "48k", "small": "40k", "app": "audio", "frame": "20", "max": 60 * 1024}}
ONSET_LIMIT_MS = 80             # Golden rule 7: each line starts within this of its animation beat
SILENCE_DB = -50.0              # outside its lines a track must stay this far below its peak (chapter 10: -91 dB)
GUESS = "guess"                 # beat timing that `draft` could not read from the scene; the agent must set it
MODEL = {
    "kokoro-v1.0.onnx": ("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
                         "7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5"),
    "voices-v1.0.bin": ("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
                        "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d"),
}
ENGINE = "kokoro-82M v1.0 (Apache-2.0) via kokoro-onnx 0.6.1"
ELEVEN_MODEL = "eleven_multilingual_v2"
ENGINES = {                     # the owner picks one per batch; the agent must ask (see README "Choosing the voice engine")
    "kokoro": {"voice": "af_heart", "label": ENGINE},
    "elevenlabs": {"voice": "Xb7hH8MSUJpSbSDYk0k2", "label": f"ElevenLabs {ELEVEN_MODEL} (paid API)"},   # "Alice", clear educator
    "breeze": {"voice": "lecturer-woman", "label": "Breeze TTS 2 (Breeze-TTS-2.cpp q8_0, local)"},
}
DEFAULT_ENGINE = "kokoro"       # scripts written before engines existed are Kokoro
# Owner's ElevenLabs standard (Oct 2026): a different voice per question, women and men taking turns, chosen from the
# QID number so a card keeps its voice on every run. Premade English voices only (never the owner's cloned voices).
ELEVEN_VOICES = [("Jessica", "cgSgspJ2msm6clMCkdW9", "woman"), ("Brian", "nPczCjzI2devNBz1zQrb", "man"),
                 ("Lily", "pFZP5JQG7iQjIQuC4Bku", "woman"), ("George", "JBFqnCBsd6RMkjVDRZzb", "man"),
                 ("Sarah", "EXAVITQu4vr4xnSDxMaL", "woman"), ("Daniel", "onwK4e9ZLuTAKqWW03F9", "man")]
ENGINE_QUALITY = {"kokoro": "standard", "elevenlabs": "high", "breeze": "medium"}   # ElevenLabs is always made at high quality
# Breeze TTS 2 (owner's choice, Oct 2026): free and local, slow on a CPU (about 10 s of work per second of speech), so every
# reply is cached. It reads words itself: the lexicon's 'say' and 'say_breeze' rewrites apply, its IPA entries do not.
BREEZE = {"repo": "https://github.com/HoppouAI/Breeze-TTS-2.cpp", "commit": "a0e177f91242ebbd2ea8d61548d742c89e4b9e06",
          "model": ("https://huggingface.co/HoppouAI/Breeze-TTS-2.cpp/resolve/main/breeze-tts-2-q8_0.gguf",
                    "a02bcc4b69b0601032727f8040c4942149b1b73aa0f69022fe5aaa6a8f0ef879")}
BREEZE_SEED = 11
BREEZE_REF_TEXT = "Good morning, everyone. Today we will look at one important topic together."
# Voice design: each voice is invented once from its description, then every line clones that recording, so a voice never
# drifts between lines or lessons. A free description works too (pass it as the voice).
BREEZE_VOICES = {
    "lecturer-woman": "A clear, warm female medical lecturer with a calm, confident, natural delivery.",
    "lecturer-man": "A clear, warm male medical lecturer with a calm, confident, natural delivery.",
    "doctor-man": "A middle-aged British male doctor with a deep, warm, calm voice, speaking clearly and steadily like a senior "
                  "consultant teaching students.",
    "doctor-woman": "A middle-aged female doctor with a warm, assured voice, speaking clearly and steadily like a senior consultant.",
    "student-woman": "A young female medical student with a bright, friendly, curious voice and a lively, natural delivery.",
    "student-man": "A young male medical student with a friendly, curious voice and a lively, natural delivery."}


# Owner's standard (Oct 2026): a different Breeze voice per question, women and men taking turns.
BREEZE_ROTATION = ["lecturer-woman", "doctor-man", "student-woman", "lecturer-man", "doctor-woman", "student-man"]


def engine_voice(engine: str, qid: str = "") -> str:
    """The voice a new or switched script gets: ElevenLabs and Breeze rotate by QID (women and men taking turns, so a
    question keeps its voice on every run), Kokoro keeps its one voice."""
    digits = re.sub(r"\D", "", qid or "")
    if engine == "elevenlabs" and digits: return ELEVEN_VOICES[int(digits) % len(ELEVEN_VOICES)][1]
    if engine == "breeze" and digits: return BREEZE_ROTATION[int(digits) % len(BREEZE_ROTATION)]
    return ENGINES[engine]["voice"]


def doc_quality(doc: dict) -> str:
    return doc.get("quality") or ENGINE_QUALITY.get(doc.get("engine", DEFAULT_ENGINE), "standard")
DEFAULT_VOICE, DEFAULT_LANG, DEFAULT_SPEED = ENGINES[DEFAULT_ENGINE]["voice"], "en-us", 1.05
SAMPLE_TEXT = "The femur is the longest bone in the body. It joins the hip to the knee and carries your weight."
CAPTION = re.compile(r"^\s*(\d+)\s*·\s*(.+)$", re.S)
CAPS_CALL = re.compile(r"\bcaps\s*\(\s*api\s*,\s*\w+\s*,\s*(\[\s*\[.*?\]\s*\])\s*\)", re.S)
NUMBERS = {w: str(i) for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
                                           "fifteen sixteen seventeen eighteen nineteen twenty".split())}


# ---------------------------------------------------------------- helpers (pure, unit-tested)
def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""): h.update(c)
    return h.hexdigest()


def load_lexicon(path: Path = HERE / "lexicon.json") -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def beats_from_scene(scene: dict) -> list[dict]:
    """The numbered captions ("1 · …") with their show windows are the card's beats.
    A script-drawn card without them may declare its captions as caps(api, P, [[start_ms, end_ms, "text", colour], …])."""
    out = []
    for l in scene.get("layers", []):
        if l.get("type") not in ("text", "label") or not isinstance(l.get("show"), list): continue
        m = CAPTION.match(str(l.get("text", "")))
        if m: out.append({"n": int(m.group(1)), "start_ms": int(l["show"][0]), "end_ms": int(l["show"][1]), "caption": m.group(2).strip()})
    out = out or beats_from_script(scene)
    out.sort(key=lambda b: b["start_ms"])
    return out


def beats_from_script(scene: dict) -> list[dict]:
    """Captions a scene script passes to caps(): [start_ms, end_ms (0 = to the end of the card), "text", colour?]."""
    out = []
    for m in CAPS_CALL.finditer(str(scene.get("script") or "")):
        try: rows = json.loads(m.group(1))
        except ValueError: continue
        for r in rows:
            if isinstance(r, list) and len(r) >= 3 and isinstance(r[0], int) and isinstance(r[1], int) and isinstance(r[2], str):
                out.append({"start_ms": r[0], "end_ms": r[1] or int(scene["duration_ms"]), "caption": r[2].strip()})
    return out


def guess_beats(duration_ms: int) -> list[dict]:
    """Even beats for a scene without numbered captions (e.g. a script-drawn card). Their times are a guess:
    the agent sets them to the animation's steps, and synth refuses the card until it has."""
    n = 3 if duration_ms <= 10000 else 4
    edges = [round(duration_ms * i / n / 100) * 100 for i in range(n + 1)]
    return [{"start_ms": a, "end_ms": b, "timing": GUESS, "caption": "", "say": "EDIT: say what the animation shows here"}
            for a, b in zip(edges, edges[1:])]


def draft_doc(scene: dict, voice=DEFAULT_VOICE, lang=DEFAULT_LANG, engine=DEFAULT_ENGINE) -> dict:
    beats = beats_from_scene(scene)
    return {"qid": scene["qid"], "duration_ms": int(scene["duration_ms"]), "engine": engine, "voice": voice, "lang": lang, "speed": DEFAULT_SPEED,
            "quality": ENGINE_QUALITY[engine],
            "beats": [{"start_ms": b["start_ms"], "end_ms": b["end_ms"], "caption": b["caption"],
                       "say": b["caption"]} for b in beats] or guess_beats(int(scene["duration_ms"]))}   # say pre-filled: synth says if too long


def retime(doc: dict, scene: dict) -> tuple[bool, str | None]:
    """Keep a kept script in step with its scene: when the captions move (same count), move the beats with them."""
    beats = beats_from_scene(scene)
    if not beats: return False, None
    if len(beats) != len(doc["beats"]):
        return False, (f"the scene now has {len(beats)} numbered captions but voice/{doc['qid']}.voice.json has {len(doc['beats'])} beats: "
                       f"run `draft --force --qids {doc['qid']}` (re-drafts its lines from the captions) or edit its beats to match")
    old = (doc["duration_ms"], [(b["start_ms"], b["end_ms"]) for b in doc["beats"]])
    doc["duration_ms"] = int(scene["duration_ms"])
    for b, c in zip(doc["beats"], beats): b["start_ms"], b["end_ms"], b["caption"] = c["start_ms"], c["end_ms"], c["caption"]; b.pop("timing", None)
    return old != (doc["duration_ms"], [(b["start_ms"], b["end_ms"]) for b in doc["beats"]]), None


def window_ms(doc: dict, i: int) -> int:
    """Time a beat's clip may last: from its start (+lead) to the next beat (−tail); the last beat may run to the end hold."""
    b = doc["beats"][i]; lead = FIRST_LEAD_MS if i == 0 else LEAD_MS
    end = doc["duration_ms"] - END_HOLD_MS if i == len(doc["beats"]) - 1 else b["end_ms"] - TAIL_MS
    return end - b["start_ms"] - lead


def max_words(doc: dict, i: int, wps: float = 2.6) -> int:
    """Rough word budget for a beat at normal speed (Kokoro af_heart ≈ 2.5–2.7 words/s)."""
    return max(1, int(window_ms(doc, i) / 1000 * wps))


def script_problems(doc: dict) -> list[tuple[int | None, str]]:
    """Everything wrong with a script that can be seen without speaking it, each with its fix: (beat index or None, message)."""
    qid, beats, out = doc["qid"], doc.get("beats", []), []
    if not beats: return [(None, f"{qid}: voice.json has no beats: run `draft --force --qids {qid}`")]
    if any(b.get("timing") == GUESS for b in beats):
        return [(None, f"{qid}: the scene has no numbered captions ('1 · …' text layers with show:[a,b], or a caps() call), so voice/{qid}.voice.json has "
                       f"{len(beats)} guessed beats. Set each beat's start_ms/end_ms to when that step of the animation starts and ends "
                       f"(read the scene's script), write its 'say' line, delete its \"timing\": \"guess\", then run make again")]
    prev_end = 0
    for i, b in enumerate(beats):
        n, say = f"{qid} beat {i+1}", str(b.get("say", "")).strip()
        if not (prev_end <= b["start_ms"] < b["end_ms"] <= doc["duration_ms"]):
            out.append((i, f"{n}: start_ms/end_ms {b['start_ms']}–{b['end_ms']} must be in order, not overlap the previous beat "
                           f"(ends {prev_end}) and stay inside the card (0–{doc['duration_ms']} ms)"))
        elif window_ms(doc, i) < MIN_WINDOW_MS:
            out.append((i, f"{n}: only {window_ms(doc, i)} ms to speak in ({b['start_ms']}–{b['end_ms']} ms minus lead/tail): "
                           f"merge it with a neighbouring beat or give its caption more time"))
        if not say or say.startswith("EDIT:"): out.append((i, f"{n}: write the spoken line ('say') first"))
        prev_end = max(prev_end, b["end_ms"])
    return out


def script_sha(doc: dict) -> str:
    """Fingerprint of everything synth reads from a script, so check can tell when the script changed after synth."""
    return hashlib.sha256(json.dumps(doc, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def spoken_text(text: str, lex: dict) -> str:
    """Apply 'say' rewrites (abbreviations, symbols) before phonemising. A key is matched as a whole token, but a symbol
    may touch a word or number ('INR↑', 'glucose→fat', '37°C', '50%')."""
    for k, v in lex.get("say", {}).items():
        pre, post = (r"(?<!\w)" if re.match(r"\w", k[0]) else ""), (r"(?!\w)" if re.match(r"\w", k[-1]) else "")
        text = re.sub(pre + re.escape(k) + post, lambda m: f" {v} ", text)
    return re.sub(r"\s+([,.;:!?])", r"\1", re.sub(r"\s+", " ", text)).strip()


def ipa_split(text: str, ipa: dict) -> list[tuple[str, bool]]:
    """Split text into (chunk, is_ipa) so dictionary words get their exact IPA and the rest is phonemised normally."""
    if not ipa: return [(text, False)]
    pat = re.compile(r"(?<![\w-])(" + "|".join(sorted(map(re.escape, ipa), key=len, reverse=True)) + r")(?![\w-])", re.I)
    out, pos = [], 0
    for m in pat.finditer(text):
        if m.start() > pos: out.append((text[pos:m.start()], False))
        out.append((ipa[next(k for k in ipa if k.lower() == m.group(1).lower())], True)); pos = m.end()
    if pos < len(text): out.append((text[pos:], False))
    return out


def canon(w: str) -> str:
    """One spelling for comparing what was said with what the (American) recogniser wrote: anaemia/anemia, litre/liter,
    tumour/tumor, -ise/-ize, number words as digits, and y/i ('Billy Rubin' = bilirubin). Doubled letters stay
    (collapsing them would let 'clothing' pass for 'clotting')."""
    w = NUMBERS.get(w, w)
    w = re.sub(r"is(e|ed|es|ing|ation)$", r"iz\1", re.sub(r"our$", "or", re.sub(r"([^aeiou])re$", r"\1er", re.sub(r"ae|oe", "e", w))))
    return w.replace("y", "i")


def norm_words(text: str) -> list[str]:
    return [canon(w) for w in re.sub(r"[^a-z0-9 ]", " ", text.lower().replace("-", "").replace("%", " percent ")).split() if w]


def word_score(expected: str, heard: str) -> float:
    """Best character-level match of the expected words against any run of heard words.
    Joined words, so ASR spacing ('pro thrombin') is not an error; best window, so an ASR repeat is not either."""
    a, hw = "".join(norm_words(expected)), norm_words(heard)
    if not a: return 1.0
    n = len(norm_words(expected)); best = 0.0
    for size in range(max(1, n - 2), n + 3):
        for i in range(0, max(1, len(hw) - size + 1)):
            best = max(best, SequenceMatcher(None, a, "".join(hw[i:i + size])).ratio())
    return best


def word_errors(expected: str, heard: str, min_len: int = 5, thr: float = 0.9) -> list[tuple[str, str]]:
    """Long words (5+ letters) that were not heard: each must closely match some stretch of the heard letters.
    One wrong sound in one long word ('ketosidosis', 'clothing', 'hyperkalaemia') barely moves the whole-line score."""
    b, out = "".join(norm_words(heard)), []
    for w in norm_words(expected):
        if len(w) < min_len: continue
        best, got = 0.0, ""
        for n in range(len(w) - 2, len(w) + 3):
            for i in range(0, max(1, len(b) - n + 1)):
                r = SequenceMatcher(None, w, b[i:i + n], autojunk=False).ratio()
                if r > best: best, got = r, b[i:i + n]
        if best < thr: out.append((w, got))
    return out


def extra_chars(expected: str, heard: str) -> int:
    """How much more was heard than said (letters only, so 'I N R' for 'INR' costs nothing)."""
    return len("".join(norm_words(heard))) - len("".join(norm_words(expected)))


def too_much_heard(expected: str, heard: str) -> bool:
    """More speech than the line holds: an extra phrase in the clip (a word-score window alone would hide it)."""
    return extra_chars(expected, heard) > max(12, len("".join(norm_words(expected))) // 2)


# ---------------------------------------------------------------- model and browser
def model_paths() -> tuple[Path, Path]:
    return CACHE / "kokoro-v1.0.onnx", CACHE / "voices-v1.0.bin"


def chromium() -> str | None:
    """The Chromium for review videos and the browser test: MOTIONCARDS_CHROMIUM, else the one `setup` found, else Playwright's own."""
    exe = os.environ.get("MOTIONCARDS_CHROMIUM")
    if exe: return exe
    try: exe = CHROMIUM_FILE.read_text(encoding="utf-8").strip()
    except OSError: return None
    return exe if exe and Path(exe).is_file() else None


def browser_works(exe: str | None = None) -> bool:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p: p.chromium.launch(**({"executable_path": exe} if exe else {})).close()
        return True
    except Exception:
        return False


def find_chromium() -> str | None:
    """A Chromium already on this machine (any recent build works with the pinned Playwright)."""
    roots = [Path(r) for r in (os.environ.get("PLAYWRIGHT_BROWSERS_PATH"), Path.home() / ".cache" / "ms-playwright") if r]
    cands = [r / "chromium" for r in roots]
    cands += sorted((c for r in roots for c in r.glob("chromium-*/chrome-linux*/chrome")), reverse=True)
    cands += [Path(w) for w in map(shutil.which, ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable")) if w]
    return next((str(c) for c in cands if c.is_file() and os.access(c, os.X_OK) and browser_works(str(c))), None)


def setup_browser():
    """Review videos and the browser test need a Chromium. Use Playwright's own, else one on the machine, else install it (free)."""
    CHROMIUM_FILE.unlink(missing_ok=True)
    if os.environ.get("MOTIONCARDS_CHROMIUM") or browser_works(): print("ok chromium", os.environ.get("MOTIONCARDS_CHROMIUM") or "(Playwright's own)"); return
    exe = find_chromium()
    if not exe:
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)
        if browser_works(): print("ok chromium (installed by Playwright)"); return
        print("WARNING: no Chromium works; review videos and the browser test need one: set MOTIONCARDS_CHROMIUM=/path/to/chrome"); return
    CHROMIUM_FILE.write_text(exe + "\n", encoding="utf-8"); print("ok chromium", exe)


def download_resuming(url: str, part: Path, attempts: int = 5):
    """Download into `part`, continuing a cut-off transfer (HTTP Range) instead of starting again."""
    import time
    for attempt in range(1, attempts + 1):
        have = part.stat().st_size if part.exists() else 0
        req = urllib.request.Request(url, headers={"Range": f"bytes={have}-"} if have else {})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                if have and r.status != 206: have = 0     # server ignored the range: start over
                with open(part, "ab" if have else "wb") as f: shutil.copyfileobj(r, f, 1 << 20)
            return
        except urllib.error.HTTPError as exc:
            if exc.code == 416: return                   # already complete; the SHA-256 check decides
            if attempt == attempts: raise
        except (OSError, urllib.error.URLError):
            if attempt == attempts: raise
        print(f"  download interrupted, resuming ({attempt}/{attempts - 1})"); time.sleep(3 * attempt)


def fetch_pinned(url: str, digest: str, p: Path):
    if not p.exists() or sha256(p) != digest:
        print("downloading", p.name); part = p.with_name(p.name + ".part"); download_resuming(url, part)
        got = sha256(part)                             # checked before it gets its real name: an interrupted download never looks complete
        if got != digest: part.unlink(); sys.exit(f"{p.name}: SHA-256 mismatch ({got}); refusing to use it")
        os.replace(part, p)
    print("ok", p.name, digest[:12])


def cmd_setup(a):
    CACHE.mkdir(parents=True, exist_ok=True)
    for name, (url, digest) in MODEL.items(): fetch_pinned(url, digest, CACHE / name)
    if "breeze" in ([getattr(a, "engine", None)] + list(getattr(a, "engines", None) or [])): setup_breeze()
    setup_browser()


def breeze_paths() -> tuple[Path, Path]:
    d = CACHE / "breeze"
    return d / "src" / "build-portable" / "breeze-cli", d / "breeze-tts-2-q8_0.gguf"


def setup_breeze():
    """Build the pinned Breeze-TTS-2.cpp commit for the CPU (no Vulkan, no server) and fetch the pinned q8_0 model."""
    cli, model = breeze_paths(); src = cli.parents[1]; src.parent.mkdir(parents=True, exist_ok=True)
    if not cli.exists():
        run = lambda *c: subprocess.run(c, check=True)
        if not src.exists(): run("git", "clone", "-q", BREEZE["repo"], str(src))
        # The pinned commit is no longer on any upstream branch, so a plain clone does not contain it: fetch it by id.
        run("git", "-C", str(src), "fetch", "-q", "origin", BREEZE["commit"])
        run("git", "-C", str(src), "checkout", "-q", BREEZE["commit"])
        run("git", "-C", str(src), "submodule", "update", "--init", "--recursive", "-q")
        # GGML_NATIVE=OFF: a portable AVX2 build. The default (-march=native) crashes without a message ("Breeze failed: ")
        # when the built binary is reused on another machine, e.g. a cloud environment's cached container on a different CPU.
        run("cmake", "-S", str(src), "-B", str(cli.parent), "-DCMAKE_BUILD_TYPE=Release", "-DBREEZE_VULKAN=OFF",
            "-DBREEZE_BUILD_SERVER=OFF", "-DGGML_NATIVE=OFF")
        run("cmake", "--build", str(cli.parent), "-j", str(os.cpu_count() or 2))
    print("ok breeze-cli", BREEZE["commit"][:12])
    fetch_pinned(*BREEZE["model"], model)


_K = None
def kokoro():
    global _K
    if _K is None:
        from kokoro_onnx import Kokoro
        m, v = model_paths()
        if not m.exists(): sys.exit("model missing: run `voiceover.py setup` first")
        _K = Kokoro(str(m), str(v))
    return _K


def phonemes(text: str, lang: str, lex: dict) -> str:
    k = kokoro(); ipa = lex.get("ipa", {}).get(lang, {})
    parts = []
    for chunk, is_ipa in ipa_split(spoken_text(text, lex), ipa):
        if is_ipa: parts.append(chunk)
        elif chunk.strip(): parts.append(k.tokenizer.phonemize(chunk, lang=lang))
    return " ".join(p.strip() for p in parts if p.strip())


def trim_lead(s, rel_db=-35.0, keep_ms=8):
    """Cut the model's leading silence so the first word starts exactly where the clip is placed (Golden rule 7)."""
    import numpy as np
    n = SR // 200; frames = len(s) // n
    if frames == 0: return s
    rms = np.sqrt(np.mean(s[:frames * n].reshape(frames, n) ** 2, axis=1) + 1e-12)
    first = int(np.argmax(rms > rms.max() * 10 ** (rel_db / 20)))
    return s[max(0, first * n - SR * keep_ms // 1000):]


def eleven_pcm(text: str, voice: str, speed: float) -> bytes:
    """ElevenLabs text-to-speech as raw 16-bit PCM at SR. Cached on disk: synth re-speaks a line to fit it, and each call costs credits."""
    body = json.dumps({"text": text, "model_id": ELEVEN_MODEL,
                       "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "speed": round(max(0.7, min(1.2, speed)), 3)}})
    cached = CACHE / "elevenlabs" / (hashlib.sha256((voice + body).encode()).hexdigest() + ".pcm")
    if cached.exists(): return cached.read_bytes()
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key: raise ValueError("engine elevenlabs needs ELEVENLABS_API_KEY in the environment (or ask the owner to pick --engine kokoro)")
    req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=pcm_{SR}", data=body.encode(),
                                 headers={"xi-api-key": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r: pcm = r.read()
    except urllib.error.HTTPError as e:
        raise ValueError(f"ElevenLabs refused voice '{voice}': HTTP {e.code} {e.read()[:300].decode(errors='replace')}") from None
    cached.parent.mkdir(parents=True, exist_ok=True); cached.write_bytes(pcm)
    return pcm


def breeze_text(text: str, lex: dict) -> str:
    """Breeze reads words itself: 'say' rewrites plus its own 'say_breeze' respellings (a word it gets wrong).
    Vocal events such as (laugh), (sigh), (cough) and (clears throat) pass through and are performed."""
    return spoken_text(text, {"say": {**lex.get("say", {}), **lex.get("say_breeze", {})}})


def breeze_args(text: str, ref: Path | None, direction: str | None = None, design: str | None = None) -> list[str]:
    """breeze-cli arguments: voice design (a description, no reference) or a clone of the designed voice, optionally directed."""
    if design: return ["--text", text, "--instruction", design, "--cfg-scale", "4"]
    args = ["--text", text, "--ref-audio", str(ref), "--ref-text", BREEZE_REF_TEXT]
    return args + (["--instruction", direction, "--cfg-scale", "4"] if direction else [])


def _breeze_run(args: list[str], out: Path):
    cli, model = breeze_paths()
    if not (cli.exists() and model.exists()): raise ValueError("Breeze is not set up: run voiceover.py setup --engine breeze")
    out.parent.mkdir(parents=True, exist_ok=True); part = out.with_name(out.stem + ".part.wav")
    r = subprocess.run([str(cli), str(model), "--cpu", "--seed", str(BREEZE_SEED), *args, "--output", str(part)],
                       capture_output=True, text=True)
    if r.returncode or not part.exists(): raise ValueError("Breeze failed: " + (r.stderr or r.stdout)[-300:])
    os.replace(part, out)                              # cached under its final name only when complete


def breeze_wav(text: str, voice: str, direction: str | None = None) -> Path:
    """The cached recording of one line. Same voice, direction and text give the same file without running the model again."""
    desc = BREEZE_VOICES.get(voice, voice)
    key = lambda *parts: hashlib.sha256(json.dumps([BREEZE["model"][1], BREEZE_SEED, *parts]).encode()).hexdigest()
    ref = CACHE / "breeze" / "voices" / (key("voice", desc) + ".wav")
    if not ref.exists(): _breeze_run(breeze_args(BREEZE_REF_TEXT, None, design=desc), ref)
    out = CACHE / "breeze" / "lines" / (key("line", desc, direction, text) + ".wav")
    if not out.exists(): _breeze_run(breeze_args(text, ref, direction), out)
    return out


def speak(text: str, voice: str, lang: str, speed: float, lex: dict, engine: str = DEFAULT_ENGINE, direction: str | None = None):
    import numpy as np
    if engine == "breeze":                             # no speed control in the model: tempo is changed afterwards, pitch kept
        af = f"atempo={speed:.3f}" if abs(speed - 1) > 1e-3 else "anull"
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(breeze_wav(breeze_text(text, lex), voice, direction)), "-af", af,
                            "-ar", str(SR), "-ac", "1", "-f", "f32le", "-"], capture_output=True)
        if r.returncode: raise ValueError("ffmpeg failed: " + r.stderr.decode()[-300:])
        s = trim_lead(np.frombuffer(r.stdout, np.float32).copy())
        return trim_lead(s[::-1])[::-1].copy()         # trim the tail as well
    if engine == "elevenlabs":                         # reads words itself: 'say' rewrites apply, IPA entries are Kokoro-only
        return trim_lead(np.frombuffer(eleven_pcm(spoken_text(text, lex), voice, speed), "<i2").astype(np.float32) / 32768)
    if engine != "kokoro": raise ValueError(f"unknown voice engine '{engine}': use one of {', '.join(ENGINES)}")
    s, sr = kokoro().create(phonemes(text, lang, lex), voice=voice, speed=speed, lang=lang, is_phonemes=True)
    assert sr == SR
    return trim_lead(np.asarray(s, dtype=np.float32))


# ---------------------------------------------------------------- draft and synth
def ws_voice(ws: Path) -> Path:
    d = ws / "voice"; d.mkdir(parents=True, exist_ok=True); return d


def scenes(ws: Path, qids=None):
    for p in sorted((ws / "scenes").glob("Q*.scene.json")):
        s = json.loads(p.read_text(encoding="utf-8"))
        if not qids or s["qid"] in qids: yield s


def write_doc(p: Path, doc: dict):
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def run_draft(a) -> list[str]:
    ws = Path(a.workspace); d = ws_voice(ws); problems = []
    for s in scenes(ws, a.qids):
        p = d / f"{s['qid']}.voice.json"
        if p.exists() and not a.force:
            doc = json.loads(p.read_text(encoding="utf-8")); moved, problem = retime(doc, s)
            switched = set_engine(doc, a.engine, a.voice)
            if getattr(a, "quality", None) and doc_quality(doc) != a.quality: doc["quality"] = a.quality; switched = True
            if problem: problems.append(f"{s['qid']}: {problem}")
            elif moved or switched: write_doc(p, doc); print("retime" if moved else "engine", p.name, f"(lines kept; voice {doc.get('engine', DEFAULT_ENGINE)} {doc['voice']})")
            else: print("keep", p.name)
            continue
        engine = a.engine or DEFAULT_ENGINE
        doc = draft_doc(s, a.voice or engine_voice(engine, s["qid"]), a.lang, engine)
        if getattr(a, "quality", None): doc["quality"] = a.quality
        write_doc(p, doc)
        if any(b.get("timing") == GUESS for b in doc["beats"]): print("draft", p.name, "beats GUESSED: no numbered captions in the scene")
        else: print("draft", p.name, "budgets (words):", [max_words(doc, i) for i in range(len(doc["beats"]))])
    if not (ws / "scenes").is_dir(): problems.append(f"no scenes folder in {ws}: the workspace needs scenes/Q*.scene.json")
    return problems


def set_engine(doc: dict, engine: str | None, voice: str | None) -> bool:
    """Point a kept script at the engine (and voice) the owner chose; its lines and timing stay. True if it changed."""
    old = (doc.get("engine", DEFAULT_ENGINE), doc["voice"])
    if engine and engine != old[0]:
        doc["engine"], doc["voice"], doc["quality"] = engine, voice or engine_voice(engine, doc.get("qid", "")), ENGINE_QUALITY[engine]
    elif voice: doc["voice"] = voice
    doc.setdefault("engine", old[0])
    return (doc["engine"], doc["voice"]) != old


def encode_opus(pcm, out: Path, bitrate: str = BITRATE, app: str = "voip", frame: str = "60"):
    """Loudness-normalise to −16 LUFS and encode Opus mono (16 kbps by default), bit-exact (same input → same bytes)."""
    import numpy as np
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", str(SR), "-ac", "1",
                        "-c:a", "libopus", "-b:a", bitrate, "-vbr", "on", "-application", app, "-frame_duration", frame,
                        "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:a", "+bitexact", str(out)],
                       input=np.asarray(pcm, np.float32).tobytes(), capture_output=True)
    if r.returncode: raise ValueError(f"{out.stem}: ffmpeg failed: " + r.stderr.decode()[-400:])


def synth_one(doc: dict, d: Path, lex: dict) -> dict:
    import numpy as np
    qid, engine = doc["qid"], doc.get("engine", DEFAULT_ENGINE); clips, cues = [], []
    if engine not in ENGINES: raise ValueError(f"{qid}: unknown engine '{engine}' in voice.json: use one of {', '.join(ENGINES)}")
    for ext in (".opus", ".track.json"): (d / f"{qid}{ext}").unlink(missing_ok=True)   # a card that fails keeps no stale voice
    found = script_problems(doc); problems = [m for _, m in found]; skip = {i for i, _ in found}
    if None in skip: raise ValueError("\n".join(problems))
    for i, b in enumerate(doc["beats"]):
        if i in skip: continue                         # still speak the other beats, so their problems show up in this pass too
        say = b["say"].strip()
        speed, win = min(MAX_SPEED, float(b.get("speed", doc.get("speed", DEFAULT_SPEED)))), window_ms(doc, i)
        clip = speak(say, doc["voice"], doc["lang"], speed, lex, engine)
        ms = len(clip) * 1000 / SR
        for faster in (min(MAX_SPEED, speed * ms / win * 1.02), MAX_SPEED):   # Golden rule 7: the line must finish inside its beat
            if ms <= win or faster <= speed: continue                       # (Kokoro is not exactly 1/speed: try the cap too)
            speed = faster; clip = speak(say, doc["voice"], doc["lang"], speed, lex, engine); ms = len(clip) * 1000 / SR
        if ms > win:
            n = len(say.split())
            problems.append(f"{qid} beat {i+1}: '{say}' ({n} words) needs {ms:.0f} ms even at {MAX_SPEED}x, the beat allows {win} ms: "
                            f"cut it to about {max(1, int(n * win / ms))} words"); continue
        at = b["start_ms"] + (FIRST_LEAD_MS if i == 0 else LEAD_MS)
        clips.append((at, clip)); cues.append({"t_ms": at, "end_ms": round(at + ms), "text": say, "speed": round(speed, 3)})
    if problems: raise ValueError("\n".join(problems))      # every problem of the card at once: one editing pass fixes all
    total = max(at * SR // 1000 + len(c) for at, c in clips) + SR // 10
    track = np.zeros(total, np.float32)
    for at, c in clips: s0 = at * SR // 1000; track[s0:s0 + len(c)] += c
    Q = QUALITY[doc_quality(doc)]
    out = d / f"{qid}.opus"; rate = Q["bitrate"]; encode_opus(track, out, rate, Q["app"], Q["frame"])
    if out.stat().st_size > Q["max"]: rate = Q["small"]; encode_opus(track, out, rate, Q["app"], Q["frame"])   # long card: keep rule 5
    size = out.stat().st_size
    if size > Q["max"]:
        out.unlink(); words = sum(len(c["text"].split()) for c in cues)
        raise ValueError(f"{qid}: voice is {size/1024:.1f} KB even at {rate}bps, over the {Q['max']//1024} KB per-card "
                         f"budget (Golden rule 5): cut about {math.ceil(words * (1 - Q['max'] / size))} of its {words} words")
    info = {"qid": qid, "file": out.name, "mime": "audio/ogg; codecs=opus", "bytes": size, "sha256": sha256(out),
            "track_ms": round(total * 1000 / SR), "card_ms": doc["duration_ms"], "voice": doc["voice"], "lang": doc["lang"],
            "engine": ENGINES[engine]["label"], "bitrate": rate, "script_sha256": script_sha(doc), "cues": cues}
    (d / f"{qid}.track.json").write_text(json.dumps(info, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return info


def run_synth(a) -> tuple[list[str], set]:
    ws = Path(a.workspace); d = ws_voice(ws); lex = load_lexicon(); rows, bad, failed = [], [], set()
    for p in sorted(d.glob("Q*.voice.json")):
        doc = json.loads(p.read_text(encoding="utf-8"))
        if a.qids and doc["qid"] not in a.qids: continue
        try: info = synth_one(doc, d, lex); rows.append(info)
        except ValueError as e: bad.append(str(e)); failed.add(doc["qid"]); continue
        except Exception as e: bad.append(f"{doc['qid']}: {type(e).__name__}: {e}"); failed.add(doc["qid"]); continue
        print(f"{info['qid']}  {info['bytes']/1024:5.1f} KB  {info['track_ms']/1000:4.1f} s  {info['bitrate']}bps  speeds {[c['speed'] for c in info['cues']]}")
    if rows: print(f"total {sum(r['bytes'] for r in rows)/1024:.1f} KB for {len(rows)} cards, average {sum(r['bytes'] for r in rows)/len(rows)/1024:.1f} KB")
    return bad, failed


# ---------------------------------------------------------------- check (ASR round trip + waveform)
def pcm16k(path: Path):
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32)


def frame_rms(pcm, sr=16000, frame_ms=10):
    import numpy as np
    n = sr * frame_ms // 1000; frames = len(pcm) // n
    return np.sqrt(np.mean(pcm[:frames * n].reshape(frames, n) ** 2, axis=1) + 1e-12)


def speech_onsets(pcm, cues, sr=16000, frame_ms=10, rel_db=-30.0) -> list[int | None]:
    """Exact sync measure from the waveform: first 10 ms frame above (peak − 30 dB) near each cue.
    The search starts 400 ms early, but never before the previous line has ended (its tail is not this line's start)."""
    rms = frame_rms(pcm, sr, frame_ms); frames = len(rms)
    if frames == 0: return [None] * len(cues)
    thr = rms.max() * 10 ** (rel_db / 20); out = []
    for k, c in enumerate(cues):
        early = c["t_ms"] - 400 if k == 0 else max(c["t_ms"] - 400, cues[k - 1]["end_ms"] + frame_ms)
        lo, hi = max(0, early // frame_ms), min(frames, (c["t_ms"] + 400) // frame_ms)
        hit = next((i for i in range(lo, hi) if rms[i] > thr), None)
        out.append(None if hit is None else hit * frame_ms - c["t_ms"])
    return out


def stray_sound(pcm, cues, sr=16000, frame_ms=10, before_ms=60, after_ms=150, rel_db=SILENCE_DB) -> list[int]:
    """Where (ms) sound starts outside every spoken line. The track is silence plus its lines, so this must be empty."""
    rms = frame_rms(pcm, sr, frame_ms); frames = len(rms)
    if frames == 0: return []
    inside = [False] * frames
    for c in cues:
        for i in range(max(0, (c["t_ms"] - before_ms) // frame_ms), min(frames, (c["end_ms"] + after_ms) // frame_ms)): inside[i] = True
    thr = rms.max() * 10 ** (rel_db / 20)
    loud = [rms[i] > thr and not inside[i] for i in range(frames)]
    return [i * frame_ms for i in range(frames) if loud[i] and (i == 0 or not loud[i - 1])]


def cue_span(cues, k, track_ms) -> tuple[int, int]:
    """The audio (ms) the recogniser hears for one line: the line plus 150 ms each side, never into its neighbours."""
    c = cues[k]
    return (max(0, c["t_ms"] - 150, cues[k - 1]["end_ms"] if k else 0),
            min(track_ms, c["end_ms"] + 150, cues[k + 1]["t_ms"] if k + 1 < len(cues) else track_ms))


def run_check(a, skip=()) -> list[str]:
    ws = Path(a.workspace); d = ws_voice(ws); fails, report, asr, asr2, lex = [], [], None, None, None
    cards = {s["qid"] for s in scenes(ws, a.qids)}
    tracks = {p.name[:10] for p in d.glob("Q*.track.json") if not a.qids or p.name[:10] in a.qids}
    if cards and tracks - cards:                       # voice left over from a card that is no longer in the batch
        fails += [f"{q}: voice for a card that is not in scenes/: delete voice/{q}.opus and voice/{q}.track.json" for q in sorted(tracks - cards)]
    want = (cards or tracks) - set(skip)
    if not want and not skip: return [f"nothing to check: no scenes in {ws / 'scenes'} and no voice tracks in {d}"]
    for qid in sorted(want):
        p = d / f"{qid}.track.json"
        if not p.exists(): fails.append(f"{qid}: no voice track: run make (voice is required for every card)"); continue
        info = json.loads(p.read_text(encoding="utf-8"))
        if not (d / info["file"]).exists() or sha256(d / info["file"]) != info["sha256"]:
            fails.append(f"{qid}: audio missing or changed after synth: run synth again"); continue
        vp = d / f"{qid}.voice.json"
        if vp.exists() and info.get("script_sha256") not in (None, script_sha(json.loads(vp.read_text(encoding="utf-8")))):
            fails.append(f"{qid}: voice.json changed after synth: run synth again"); continue
        if asr is None:
            from faster_whisper import WhisperModel
            asr = WhisperModel(a.asr, device="cpu", compute_type="int8")
        pcm = pcm16k(d / info["file"]); lex = lex or load_lexicon(); track_ms = len(pcm) // 16
        onsets, stray = speech_onsets(pcm, info["cues"]), stray_sound(pcm, info["cues"])
        row = {"qid": qid, "beats": [], "stray_sound_ms": stray}
        for k, (c, onset) in enumerate(zip(info["cues"], onsets)):
            lo, hi = cue_span(info["cues"], k, track_ms)            # each line on its own: no words carried over from silence
            segs, _ = asr.transcribe(pcm[lo * 16:hi * 16], beam_size=5, temperature=0.0, word_timestamps=True,
                                     vad_filter=False, condition_on_previous_text=False)
            heard, spoken = " ".join(w.word.strip() for s in segs for w in (s.words or [])), spoken_text(c["text"], lex)
            score, wrong = word_score(spoken, heard), word_errors(spoken, heard)
            if wrong and score >= a.min_score and a.asr2:      # one long word in doubt: a larger recogniser must agree before it fails
                if asr2 is None:
                    from faster_whisper import WhisperModel
                    asr2 = WhisperModel(a.asr2, device="cpu", compute_type="int8")
                segs2, _ = asr2.transcribe(pcm[lo * 16:hi * 16], beam_size=5, temperature=0.0, word_timestamps=True,
                                           vad_filter=False, condition_on_previous_text=False)
                heard2 = " ".join(w.word.strip() for s in segs2 for w in (s.words or []))
                both = {w for w, _ in word_errors(spoken, heard2)}
                wrong = [x for x in wrong if x[0] in both]
                row["second_opinion"] = {**row.get("second_opinion", {}), str(k + 1): heard2}
            row["beats"].append({"say": c["text"], "heard": heard, "score": round(score, 3), "onset_error_ms": onset,
                                 **({"misheard": [f"{w} -> {g}" for w, g in wrong]} if wrong else {})})
            if score < a.min_score or wrong:
                what = ", ".join(f"'{w}' sounds like '{g}'" for w, g in wrong) or f"it sounds like '{heard}' ({score:.2f} < {a.min_score})"
                fails.append(f"{qid}: said '{c['text']}' but {what}: add the word to voiceover/lexicon.json ('ipa' for a mispronounced "
                             f"word, 'say' for an abbreviation or symbol), or reword the line")
            elif too_much_heard(spoken, heard):
                fails.append(f"{qid}: said '{c['text']}' but heard more: '{heard}': listen to voice/review/{qid}.mp4; re-run synth")
            if onset is None or abs(onset) > ONSET_LIMIT_MS:
                fails.append(f"{qid}: beat '{c['text'][:30]}…' starts {onset} ms off its animation beat (limit ±{ONSET_LIMIT_MS} ms): re-run synth")
        if stray: fails.append(f"{qid}: sound outside the spoken lines at {stray} ms (must be silent below {SILENCE_DB:.0f} dB): re-run synth")
        report.append(row)
        print(qid, " | ".join(f"{b['score']:.2f} {b['onset_error_ms']:+d}ms" if b['onset_error_ms'] is not None else f"{b['score']:.2f} ?" for b in row["beats"]))
    (d / "check-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    beats = [b for r in report for b in r["beats"]]
    if beats and not fails:
        on = [b["onset_error_ms"] for b in beats]
        print(f"CHECK PASS: {len(report)} cards, {len(beats)} beats; lowest word score {min(b['score'] for b in beats):.2f} (limit {a.min_score}); "
              f"beats start {min(on):+d} to {max(on):+d} ms from their animation (limit ±{ONSET_LIMIT_MS}); silent between lines")
    return fails


# ---------------------------------------------------------------- review video (owner listens on the phone)
def run_review(a) -> list[str]:
    sys.path.insert(0, str(ROOT))
    from motioncards.lib.render import render_scenes
    exe = chromium()
    if exe: os.environ["MOTIONCARDS_CHROMIUM"] = exe
    ws = Path(a.workspace).resolve(); d = ws_voice(ws); out = d / "review"; out.mkdir(exist_ok=True); fails = []  # absolute: ffmpeg resolves concat paths against the list file
    for s in scenes(ws, a.qids):
        tr = d / f"{s['qid']}.track.json"
        if not tr.exists(): continue
        fdir = out / f"frames-{s['qid']}"; step = 1000 // a.fps
        times = list(range(0, int(s["duration_ms"]) + 1, step))
        try: render_scenes([s], fdir, times=times, sizes=["phone"], sheet=False)
        except Exception as e:
            fails.append(f"{s['qid']}: review video failed ({str(e).splitlines()[0][:160]}): run `voiceover.py setup` to find a Chromium, "
                         f"or set MOTIONCARDS_CHROMIUM, or use make --no-review"); shutil.rmtree(fdir, ignore_errors=True); continue
        lst = fdir / "list.txt"
        lst.write_text("".join(f"file '{fdir}/{s['qid']}_phone_{t:05d}ms.png'\nduration {step/1000}\n" for t in times), encoding="utf-8")
        mp4 = out / f"{s['qid']}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(d / f"{s['qid']}.opus"),
                        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p", "-r", str(a.fps), "-c:v", "libx264", "-crf", "28",
                        "-preset", "veryfast", "-af", "apad", "-c:a", "aac", "-b:a", "128k", "-shortest", str(mp4)], check=True)
        shutil.rmtree(fdir, ignore_errors=True)
        print("review", mp4, f"{mp4.stat().st_size/1024:.0f} KB")
    return fails


def finish(problems: list[str], title: str = "FIX:"):
    if problems: sys.exit("\n".join([title] + problems))


def fix_list(problems: list[str]) -> list[str]:
    return [l for p in problems for l in p.split("\n") if l.strip()]


def cmd_draft(a): finish(run_draft(a))
def cmd_synth(a): finish(run_synth(a)[0])
def cmd_check(a): finish(run_check(a), "CHECK FAILED:")
def cmd_review(a): finish(run_review(a))


def need_engine(a):
    if not a.engine:
        sys.exit("Which voice engine? ASK THE OWNER first, then run again with one of:\n"
                 "  --engine kokoro       free, offline, Kokoro-82M af_heart (the project default)\n"
                 "  --engine elevenlabs   paid ElevenLabs API, needs ELEVENLABS_API_KEY\n"
                 "  --engine breeze       free, local Breeze TTS 2: designed voices, emotions, (laugh) (sigh); slow on a CPU\n"
                 "To let them listen first: voiceover.py sample --engines kokoro elevenlabs breeze")


def cmd_sample(a):
    """A short test clip per engine, same loudness and same length, so the owner can hear the difference before choosing."""
    import numpy as np
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); lex = load_lexicon()
    if "kokoro" in a.engines: cmd_setup(a)
    for engine in a.engines:
        clip = speak(a.text, ENGINES[engine]["voice"], DEFAULT_LANG, 1.0, lex, engine)
        f = out / f"{ {'elevenlabs': 'ElevenLabs', 'breeze': 'Breeze'}.get(engine, 'Kokoro')}_{a.seconds:g}s.mp3"
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                            "-af", f"loudnorm=I=-16:TP=-1.5,apad=whole_dur={a.seconds},atrim=0:{a.seconds}",
                            "-ar", "44100", "-b:a", "128k", str(f)], input=np.asarray(clip, np.float32).tobytes(), capture_output=True)
        if r.returncode: sys.exit(f"{engine}: ffmpeg failed: " + r.stderr.decode()[-400:])
        print(f"{f}  ({len(clip) / SR:.1f} s of speech, {ENGINES[engine]['label']})")


def cmd_make(a):
    """Golden rule 8: one command for the agent. Installs the model if missing, drafts every card's lines
    from its captions (existing scripts are kept, and re-timed if the captions moved), then synth -> check -> review.
    Every problem of every card is collected, so one editing pass can fix them all."""
    need_engine(a)
    cmd_setup(a)                                       # verifies the pinned model (downloads it if missing) and the browser
    problems = run_draft(a)
    bad, failed = run_synth(a); problems += bad
    problems += run_check(a, skip=failed)
    if not problems and not a.no_review: problems += run_review(a)
    problems = fix_list(problems)
    finish(problems, f"FIX ({len(problems)} problems; edit work/<batch>/voice/<QID>.voice.json or voiceover/lexicon.json as each line says, "
                     f"then run make again):")
    d = ws_voice(Path(a.workspace))
    print(f"DONE: voice for {len(list(d.glob('Q*.track.json')))} cards in {d} — now run: python tools/motioncards.py package … (it embeds the voice)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("setup"); p.set_defaults(f=cmd_setup)
    p.add_argument("--engine", choices=list(ENGINES), help="breeze: also build Breeze-TTS-2.cpp and fetch its model")
    p = sub.add_parser("sample", help="test clip per engine for the owner to compare"); p.set_defaults(f=cmd_sample)
    p.add_argument("--engines", nargs="+", choices=list(ENGINES), default=list(ENGINES)); p.add_argument("--text", default=SAMPLE_TEXT)
    p.add_argument("--seconds", type=float, default=7); p.add_argument("--out", default="work/voice-sample")
    for name, f in (("make", cmd_make), ("draft", cmd_draft), ("synth", cmd_synth), ("check", cmd_check), ("review", cmd_review), ("all", cmd_make)):
        p = sub.add_parser(name); p.set_defaults(f=f)
        p.add_argument("--workspace", required=True); p.add_argument("--qids", nargs="*")
        p.add_argument("--engine", choices=list(ENGINES), help="make: required, ask the owner; draft: engine for new or switched scripts")
        p.add_argument("--voice", help="default: kokoro af_heart; elevenlabs a different woman or man per question (ELEVEN_VOICES)"); p.add_argument("--lang", default=DEFAULT_LANG)
        p.add_argument("--force", action="store_true"); p.add_argument("--asr", default="base.en")
        p.add_argument("--asr2", default="small.en", help="check: second recogniser asked before a long word fails ('' = off)")
        p.add_argument("--min-score", type=float, default=0.85); p.add_argument("--fps", type=int, default=15)
        p.add_argument("--no-review", action="store_true", help="make: skip the review videos")
        p.add_argument("--quality", choices=list(QUALITY), help="make/draft: override the engine's quality (kokoro standard = 16 kbps, elevenlabs high = 48 kbps full-band Opus); saved in voice.json")
    a = ap.parse_args(); a.f(a)


if __name__ == "__main__":
    main()
