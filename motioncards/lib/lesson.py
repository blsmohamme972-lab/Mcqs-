"""Image lessons: one illustration plus a voice, played as a landscape lesson below each MCQ.

A lesson is written as work/<batch>/lessons/<QID>.lesson.json (the image, the spoken lines, and which part of the
image each line shows). `build_lesson` turns it into an ordinary v2 scene plus its voice track, so the existing
package, validate, bot upload, hosting and offline download all work unchanged:

- the image becomes an AVIF asset (about half the size of WebP at the same quality);
- every line is spoken with the chosen engine (voiceover/voiceover.py: kokoro, elevenlabs or breeze) and joined into
  one Opus track, with one cue per line;
- the scene script moves a camera over the image (eased zoom and pan per shot, a slow push-in while a shot holds),
  dims everything but the part being explained (spotlight), pulses a ring on it, and shows the line as a caption with
  the speaker's name. The voice is the master clock in the app, so picture and sound cannot drift.
- optional intro ("question" and "answer"): the picture is dimmed, a box shows the question (shortened when long) while
  the voice reads it, a second box below shows the answer while the voice says it, then both fade and the explanation
  starts with the camera and spotlight. While the voice reads a box, the word being said is highlighted (word times
  come from the speech recogniser listening to the clip, so they follow the real voice).
"""
from __future__ import annotations
import base64, json, math, re, subprocess, sys
from difflib import SequenceMatcher
from pathlib import Path

W, H = 960, 540                       # landscape stage (16:9)
MAX_IMAGE_BYTES = 600 * 1024          # engine_v2 asset limit
LESSON_KEYS = {"qid", "image", "takeaway", "engine", "voice", "voices", "names", "tempo", "gap_ms", "shots", "lines", "lang",
               "question", "answer"}
LINE_KEYS = {"who", "text", "say", "dir", "shot", "tag"}
INTRO_KEYS = {"text", "say", "dir"}
INTRO_MAX = {"question": 220, "answer": 110}               # characters that fit the intro boxes (about 5 and 3 lines)
INTRO_DIR = {"question": "clear, curious", "answer": "calm, confident"}
INTRO_HOLD_MS = 1100                                        # silence after the answer while the boxes fade out


def _fail(msg: str): raise ValueError("lesson: " + msg)


def check_lesson(spec: dict, qid: str) -> dict:
    """Validate a lesson spec and fill defaults. Errors name the exact field."""
    if not isinstance(spec, dict): _fail("must be a JSON object")
    extra = set(spec) - LESSON_KEYS
    if extra: _fail("unknown fields " + ", ".join(sorted(extra)))
    if spec.get("qid") != qid: _fail(f"qid must be {qid}")
    for k in ("image", "takeaway"):
        if not isinstance(spec.get(k), str) or not spec[k].strip(): _fail(f"{k} is required")
    if len(spec["takeaway"]) > 240: _fail("takeaway is longer than 240 characters")
    shots = spec.get("shots")
    if not isinstance(shots, list) or not shots: _fail("shots must be a non-empty list")
    for i, s in enumerate(shots):
        if not isinstance(s, dict) or not all(isinstance(s.get(k), (int, float)) for k in ("x", "y", "z")): _fail(f"shots[{i}] needs x, y, z")
        if not 1 <= s["z"] <= 4: _fail(f"shots[{i}].z must be 1..4")
        sp = s.get("spot")
        if sp is not None and not (isinstance(sp, list) and len(sp) == 3 and all(isinstance(v, (int, float)) for v in sp)): _fail(f"shots[{i}].spot must be [x, y, r]")
    lines = spec.get("lines")
    if not isinstance(lines, list) or not 1 <= len(lines) <= 64: _fail("lines must be a list of 1..64")
    for i, ln in enumerate(lines):
        if not isinstance(ln, dict): _fail(f"lines[{i}] must be an object")
        extra = set(ln) - LINE_KEYS
        if extra: _fail(f"lines[{i}]: unknown fields " + ", ".join(sorted(extra)))
        if not isinstance(ln.get("text"), str) or not ln["text"].strip() or len(ln["text"]) > 200: _fail(f"lines[{i}].text must be 1..200 characters")
        if not isinstance(ln.get("shot"), int) or not 0 <= ln["shot"] < len(shots): _fail(f"lines[{i}].shot must index shots")
    if ("question" in spec) != ("answer" in spec): _fail("question and answer go together (the intro needs both)")
    for k in ("question", "answer"):
        if k not in spec: continue
        b = spec[k]
        if not isinstance(b, dict): _fail(f"{k} must be an object")
        extra = set(b) - INTRO_KEYS
        if extra: _fail(f"{k}: unknown fields " + ", ".join(sorted(extra)))
        if not isinstance(b.get("text"), str) or not b["text"].strip() or len(b["text"]) > INTRO_MAX[k]: _fail(f"{k}.text must be 1..{INTRO_MAX[k]} characters")
    out = {"engine": "kokoro", "voices": {}, "names": {}, "tempo": 1.0, "gap_ms": 450, "lang": "en-us", **spec}
    if not 0.8 <= float(out["tempo"]) <= 1.25: _fail("tempo must be 0.8..1.25")
    return out


def encode_avif(src: Path, crf: int = 30, max_width: int = 1600) -> tuple[bytes, int, int]:
    """Image -> AVIF bytes (4:4:4 keeps red text and fine lines sharp). Raises the CRF until it fits the asset limit."""
    w, h = _image_size(src)
    scale = min(1.0, max_width / w); w2, h2 = round(w * scale / 2) * 2, round(h * scale / 2) * 2
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:                       # the AVIF muxer needs a seekable file, not a pipe
        out = Path(tmp) / "img.avif"
        for c in range(crf, 52, 3):
            r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", f"scale={w2}:{h2}:flags=lanczos", "-c:v", "libaom-av1",
                                "-still-picture", "1", "-crf", str(c), "-cpu-used", "3", "-pix_fmt", "yuv444p", str(out)], capture_output=True)
            if r.returncode: _fail("ffmpeg could not encode the image to AVIF: " + r.stderr.decode()[-300:])
            if out.stat().st_size <= MAX_IMAGE_BYTES: return out.read_bytes(), w2, h2
    _fail("image does not fit 600 KB even at low quality; use a smaller image")


def voice_tool():
    root = Path(__file__).resolve().parents[2] / "voiceover"
    if str(root) not in sys.path: sys.path.insert(0, str(root))
    import voiceover as V
    return V


_ASR = []                                                     # the recogniser, loaded once per run


def _tok(w: str) -> str: return re.sub(r"[^a-z0-9]", "", w.lower())


def _speech_span(clip, sr: int) -> tuple[float, float]:
    """First and last moment the clip is louder than -40 dB (in ms), for the fallback timing."""
    import numpy as np
    hop = sr // 100; n = len(clip) // hop
    if n < 2: return 0.0, len(clip) * 1000 / sr
    rms = np.sqrt(np.mean(clip[:n * hop].reshape(n, hop) ** 2, axis=1)); on = np.nonzero(rms > max(1e-4, rms.max() * 0.01))[0]
    return (float(on[0]) * 10, float(on[-1] + 1) * 10) if len(on) else (0.0, n * 10.0)


def word_times(clip, sr: int, text: str) -> list[list[int]]:
    """[start_ms, end_ms] in the clip for every word of `text` (split on spaces), as close to the voice as possible.

    The recogniser (faster-whisper base.en, already in the voice venv) hears the clip with word timestamps; heard words
    are matched to the shown words in order. Shown words it did not match (numbers, abbreviations spoken letter by
    letter) share the time between their matched neighbours by length. Without the recogniser all words share the
    spoken span by length."""
    import numpy as np
    shown = text.split(); toks = [_tok(w) for w in shown]
    lo, hi = _speech_span(clip, sr); heard = []
    try:
        if not _ASR:
            from faster_whisper import WhisperModel
            _ASR.append(WhisperModel("base.en", device="cpu", compute_type="int8"))
        x = np.interp(np.arange(0, len(clip), sr / 16000), np.arange(len(clip)), clip).astype(np.float32)
        segs, _ = _ASR[0].transcribe(x, beam_size=5, temperature=0.0, word_timestamps=True, vad_filter=False, condition_on_previous_text=False)
        heard = [(_tok(w.word), w.start * 1000, w.end * 1000) for sg in segs for w in (sg.words or []) if _tok(w.word)]
    except Exception as exc:                                     # no recogniser: the length-based timing below still works
        print(f"lesson: word timing without the recogniser ({type(exc).__name__}: {exc})", file=sys.stderr)
    times: list = [None] * len(shown)
    for blk in SequenceMatcher(None, toks, [h[0] for h in heard], autojunk=False).get_matching_blocks():
        for j in range(blk.size): times[blk.a + j] = [heard[blk.b + j][1], heard[blk.b + j][2]]
    i = 0                                                        # fill each gap between known words by word length
    while i < len(shown):
        if times[i] is not None: i += 1; continue
        j = i
        while j < len(shown) and times[j] is None: j += 1
        a = times[i - 1][1] if i else lo; b = times[j][0] if j < len(shown) else hi
        if b < a: b = a
        size = [max(1, len(toks[k]) or 1) for k in range(i, j)]; tot, acc = sum(size), a
        for k, n in zip(range(i, j), size):
            d = (b - a) * n / tot; times[k] = [acc, acc + d]; acc += d
        i = j
    out, prev = [], 0.0
    for s0, e0 in times:                                         # monotonic, never before the previous word
        s0 = max(s0, prev); e0 = max(e0, s0 + 40); out.append([round(s0), round(e0)]); prev = s0
    return out


def build_voice(spec: dict, voice_dir: Path, qid: str) -> dict:
    """Speak every line, join them with gaps into one Opus track, write <QID>.opus and <QID>.track.json."""
    import numpy as np
    V = voice_tool(); lex = V.load_lexicon(); engine = spec["engine"]
    if engine not in V.ENGINES: _fail(f"engine must be one of {', '.join(V.ENGINES)}")
    lead, gap, tail = 500, int(spec["gap_ms"]), 600
    pcm = [np.zeros(V.SR * lead // 1000, np.float32)]; t = lead; cues = []
    narrator = spec.get("voice") or V.engine_voice(engine, qid)          # one narrator: the engine's voice for this question
    if "question" in spec:                                              # intro: the question, then the answer, then a pause
        for k in ("question", "answer"):
            b = spec[k]; clip = V.speak(b.get("say") or b["text"], narrator, spec["lang"], float(spec["tempo"]), lex, engine, b.get("dir") or INTRO_DIR[k])
            ms = len(clip) * 1000 / V.SR
            words = [[round(t + a), round(t + e)] for a, e in word_times(clip, V.SR, b["text"])]
            cues.append({"t_ms": round(t), "end_ms": round(t + ms), "text": b["text"], "kind": k, "words": words})
            pause = gap if k == "question" else gap + INTRO_HOLD_MS
            pcm += [clip, np.zeros(V.SR * pause // 1000, np.float32)]; t += ms + pause
    for i, ln in enumerate(spec["lines"]):
        voice = spec["voices"].get(ln.get("who", ""), narrator)
        clip = V.speak(ln.get("say") or ln["text"], voice, spec["lang"], float(spec["tempo"]), lex, engine, ln.get("dir"))
        ms = len(clip) * 1000 / V.SR
        cues.append({"t_ms": round(t), "end_ms": round(t + ms), "text": ln["text"]})
        pcm += [clip, np.zeros(V.SR * gap // 1000, np.float32)]; t += ms + gap
    pcm[-1] = np.zeros(V.SR * tail // 1000, np.float32)                 # the last gap becomes the closing tail
    track = np.concatenate(pcm); voice_dir.mkdir(parents=True, exist_ok=True); out = voice_dir / f"{qid}.opus"
    Q = V.QUALITY[V.ENGINE_QUALITY[engine]]; V.encode_opus(track, out, Q["bitrate"], Q["app"], Q["frame"])
    info = {"qid": qid, "file": out.name, "mime": "audio/ogg; codecs=opus", "bytes": out.stat().st_size, "sha256": V.sha256(out),
            "track_ms": round(len(track) * 1000 / V.SR), "engine": V.ENGINES[engine]["label"], "bitrate": Q["bitrate"], "cues": cues}
    (voice_dir / f"{qid}.track.json").write_text(json.dumps(info, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return info


SCRIPT = r"""// Image lesson player: camera, spotlight, pulse ring and captions, all a pure function of t (the voice clock in the app).
const L = __LESSON__;
const MOVE = 1900, LEAD = 450, SPOT_IN = 750, CAP_FADE = 220;
// smootherstep: zero speed and zero acceleration at both ends, so the camera glides instead of starting and stopping
const ease = p => p * p * p * (p * (6 * p - 15) + 10), clamp = (v, a, b) => Math.max(a, Math.min(b, v)), lerp = (a, b, p) => a + (b - a) * p;
const EV = ["(laugh)", "(sigh)", "(cough)", "(clears throat)"];   // performed by the voice, never shown in the caption
const IN = 450, OUT = 600, Q_FONT = 30, A_FONT = 30, LH = 40;
let el = {}, runs = [], base = 1;
function setup(api) {
  base = Math.max(api.W / L.iw, api.H / L.ih);                  // the image covers the stage at zoom 1
  el.img = api.$("#lesson-img"); el.spot = api.$("#lesson-spot"); el.spotG = api.$("#lesson-spot-g");
  el.ring = api.$("#lesson-ring"); el.cap = api.$("#lesson-cap"); el.capBox = api.$("#lesson-cap-box"); el.tag = api.$("#lesson-tag");
  el.tagText = api.$("#lesson-tag-text");
  if (L.intro) { el.dim = api.$("#lesson-dim"); el.qG = api.$("#lesson-q"); el.aG = api.$("#lesson-a"); el.qBox = api.$("#lesson-q-box");
    el.aBox = api.$("#lesson-a-box"); el.qHead = api.$("#lesson-q-head"); el.aHead = api.$("#lesson-a-head");
    el.qHl = api.$("#lesson-q-hl"); el.aHl = api.$("#lesson-a-hl"); }
  if (L.intro) runs.push({shot: L.shots.length - 1, start: 0});  // the intro shows the whole picture (last shot)
  L.cues.forEach(c => { if (!runs.length || runs[runs.length - 1].shot !== c.shot) runs.push({shot: c.shot, start: runs.length ? c.t - LEAD : 0}); });
  runs.forEach((r, i) => r.end = i + 1 < runs.length ? runs[i + 1].start : api.D);
  // pre-wrap every caption into lines that fit the caption width
  const probe = api.el("text", {"font-size": 34, "font-weight": 700, "font-family": "system-ui, sans-serif", opacity: 0}, api.svg);
  const fits = s => { probe.textContent = s; return probe.getComputedTextLength() <= api.W * 0.88; };
  L.cues.forEach(c => {
    let words = c.text; for (const e of EV) words = words.split(e).join(" ");
    const name = c.who ? (L.names[c.who] || c.who) + "  " : "", out = []; let line = name;
    for (const w of words.split(/\s+/).filter(Boolean)) { const tryL = line ? line + (line.endsWith("  ") ? "" : " ") + w : w; if (fits(tryL) || !line.trim()) line = tryL; else { out.push(line); line = w; } }
    out.push(line); c.lines = out.slice(0, 3); c.nameLen = name.length;
  });
  if (L.intro) layoutIntro(api, probe);
  probe.remove();
}
// intro boxes: wrap the question and the answer, stack both boxes in the middle of the stage
function layoutIntro(api, probe) {
  const bw = api.W * 0.84, tw = bw - 56, wrap = (s, size) => {
    api.set(probe, {"font-size": size}); const out = []; let line = "";
    for (const w of s.split(/\s+/).filter(Boolean)) { const tryL = line ? line + " " + w : w; probe.textContent = tryL;
      if (probe.getComputedTextLength() <= tw || !line) line = tryL; else { out.push(line); line = w; } }
    out.push(line); return out;
  };
  const q = wrap(L.intro.q.text, Q_FONT).slice(0, 6), a = wrap(L.intro.a.text, A_FONT).slice(0, 4);
  const qh = 62 + LH * q.length, ah = 62 + LH * a.length, top = Math.round((api.H - qh - 22 - ah) / 2), x0 = (api.W - bw) / 2;
  // one tspan per word, so the word being said can be found and highlighted
  const fill = (id, lines, y, size) => { const g = api.$(id); g.textContent = ""; const ws = [];
    lines.forEach((ln, i) => { const row = api.el("tspan", {x: api.W / 2, y: y + i * LH, "font-size": size}, g);
      ln.split(" ").forEach((w, j) => { const sp = api.el("tspan", {}, row); sp.textContent = (j ? " " : "") + w; ws.push({sp, lead: j ? 1 : 0, row: i}); }); });
    return ws; };
  api.set(el.qBox, {x: x0, y: top, width: bw, height: qh}); api.set(el.qHead, {x: x0 + 26, y: top + 32});
  el.qWords = fill("#lesson-q-text", q, top + 70, Q_FONT);
  api.set(el.aBox, {x: x0, y: top + qh + 22, width: bw, height: ah}); api.set(el.aHead, {x: x0 + 26, y: top + qh + 54});
  el.aWords = fill("#lesson-a-text", a, top + qh + 92, A_FONT);
  // the box behind each word, from the laid-out text (pure layout, read once)
  const boxes = (id, ws, size) => { const tx = api.$(id); let ci = 0;
    return ws.map(w => { const n = w.sp.textContent.length, s = ci + w.lead, e = ci + n - 1; ci += n;
      const r0 = tx.getExtentOfChar(s), r1 = tx.getExtentOfChar(Math.max(s, e));
      return {x: r0.x - 6, y: r0.y - 2, w: r1.x + r1.width - r0.x + 12, h: size * 1.25 + 4, row: w.row}; }); };
  L.intro.q.boxes = boxes("#lesson-q-text", el.qWords, Q_FONT); L.intro.a.boxes = boxes("#lesson-a-text", el.aWords, A_FONT);
}
// the highlight glides from word to word in step with the voice; words already said keep a stronger colour
function highlight(t, api, part, hl, ws, said, ahead) {
  const W = part.words || [], B = part.boxes || []; let i = -1;
  for (let j = 0; j < Math.min(W.length, B.length); j++) if (t >= W[j][0] - 40) i = j;
  const end = W.length ? W[W.length - 1][1] + 250 : 0;
  ws.forEach((w, j) => api.set(w.sp, {fill: !W.length || (j <= i && t <= end + 2000) ? said : ahead}));
  if (i < 0 || t > end) { api.set(hl, {x: 0, y: 0, width: 10, height: 10, opacity: 0}); return; }   // fixed values: the frame depends only on t
  const b = B[i], a = i && B[i - 1].row === b.row ? B[i - 1] : b, p = ease(clamp((t - W[i][0] + 40) / 110, 0, 1));
  api.set(hl, {x: lerp(a.x, b.x, p).toFixed(1), y: b.y.toFixed(1), width: lerp(a.w, b.w, p).toFixed(1), height: b.h.toFixed(1),
               opacity: (1 - ease(clamp((t - end + 250) / 250, 0, 1))).toFixed(3)});
}
function intro(t, api) {
  if (!L.intro) return;
  const I = L.intro, out = 1 - ease(clamp((t - I.out) / OUT, 0, 1));
  highlight(t, api, I.q, el.qHl, el.qWords, "#1b2a4a", "#6d7690");
  highlight(t, api, I.a, el.aHl, el.aWords, "#ffffff", "#a9cdb9");
  const qo = ease(clamp((t - I.q.t + 350) / IN, 0, 1)) * out, ao = ease(clamp((t - I.a.t + 250) / IN, 0, 1)) * out;
  api.set(el.dim, {opacity: (0.66 * ease(clamp(t / 500, 0, 1)) * out).toFixed(3)});
  api.set(el.qG, {opacity: qo.toFixed(3), transform: `translate(0 ${(14 * (1 - qo)).toFixed(2)})`});
  api.set(el.aG, {opacity: ao.toFixed(3), transform: `translate(0 ${(14 * (1 - ao)).toFixed(2)})`});
}
function camera(t) {
  let k = 0; for (let j = 0; j < runs.length; j++) if (t >= runs[j].start) k = j;
  const r = runs[k], s = L.shots[r.shot], a = L.shots[k ? runs[k - 1].shot : r.shot];
  const p = k ? ease(clamp((t - r.start) / MOVE, 0, 1)) : 1, hold = clamp((t - r.start - MOVE) / Math.max(100, r.end - r.start - MOVE), 0, 1);
  // between two close-ups far apart the camera eases out a little mid-way, like a real camera move, then settles in
  const far = Math.hypot(s.x - a.x, s.y - a.y) / L.iw, dip = Math.min(a.z, s.z) > 1.15 ? Math.min(0.22, far * 0.5) : 0;
  let z = Math.exp(lerp(Math.log(a.z), Math.log(s.z), p)) * (1 - dip * Math.sin(Math.PI * p)) * (1 + 0.035 * ease(hold));
  if (k === 0) z = lerp(1.08, 1, ease(clamp(t / 2600, 0, 1))) * (1 + 0.035 * ease(hold));
  return {x: lerp(a.x, s.x, p), y: lerp(a.y, s.y, p), z, s, a, p, r, k};
}
function render(t, api) {
  const c = camera(t), k = base * c.z, sw = L.iw * k, sh = L.ih * k;
  const ox = clamp(api.W / 2 - c.x * k, api.W - sw, 0), oy = clamp(api.H / 2 - c.y * k, api.H - sh, 0);
  api.set(el.img, {transform: `translate(${ox.toFixed(2)} ${oy.toFixed(2)}) scale(${k.toFixed(5)})`});
  // spotlight: everything but the idea being explained fades back. Spot to spot it glides with the camera (it never
  // switches off mid-lesson); it fades in when a spot appears and fades out when the next shot has none.
  const A = c.k ? c.a.spot : null, B = c.s.spot, since = t - c.r.start;
  let sp = null, on = 0;
  if (A && B) { sp = [0, 1, 2].map(i => lerp(A[i], B[i], c.p)); on = 1; }
  else if (B) { sp = B; on = ease(clamp((since - (c.k ? MOVE * 0.55 : MOVE)) / SPOT_IN, 0, 1)); }
  else if (A) { sp = A; on = 1 - ease(clamp(since / (MOVE * 0.5), 0, 1)); }
  if (sp && on > 0) {
    const sx = ox + sp[0] * k, sy = oy + sp[1] * k, rr = sp[2] * k;
    api.set(el.spotG, {cx: sx.toFixed(1), cy: sy.toFixed(1), r: (rr * 1.4).toFixed(1)});
    const rp = B ? clamp((since - MOVE * 0.85) / 1300, 0, 1) : 0;   // one soft ring as the camera settles on the idea
    api.set(el.ring, {cx: sx.toFixed(1), cy: sy.toFixed(1), r: (rr * (0.55 + 0.45 * ease(rp))).toFixed(1), opacity: (rp > 0 && rp < 1 ? Math.sin(Math.PI * rp) * 0.75 : 0).toFixed(3)});
  } else {                                                      // no spot: fixed values, so the frame depends only on t
    api.set(el.spotG, {cx: api.W / 2, cy: api.H / 2, r: 200}); api.set(el.ring, {cx: 0, cy: 0, r: 10, opacity: 0});
  }
  api.set(el.spot, {opacity: (0.92 * on).toFixed(3)});
  // caption of the line being spoken
  let q = null; for (const cue of L.cues) if (t >= cue.t - 100 && t <= cue.e + 400) q = cue;
  if (el.capFor !== q) {
    el.capFor = q; el.cap.textContent = "";
    if (q) q.lines.forEach((ln, i) => {
      const ts = api.el("tspan", {x: api.W / 2, dy: i ? 42 : 0}, el.cap);
      if (i === 0 && q.nameLen) { api.el("tspan", {fill: L.colors[q.who] || "#ffd27a"}, ts).textContent = ln.slice(0, q.nameLen); api.el("tspan", {}, ts).textContent = ln.slice(q.nameLen); }
      else ts.textContent = ln;
    });
    const n = q ? q.lines.length : 0, h = 26 + 42 * n;
    api.set(el.cap, {y: api.H - 20 - h + 47}); api.set(el.capBox, {y: api.H - 20 - h, height: h});
    const tg = q && q.tag || ""; el.tagText.textContent = tg; api.set(el.tag, {opacity: tg ? 1 : 0});
    if (tg) api.set(api.$("#lesson-tag-box"), {width: el.tagText.getComputedTextLength() + 30});
  }
  // captions fade in and out instead of cutting (computed from t on every frame)
  const f = q ? ease(clamp((t - q.t + 100) / CAP_FADE, 0, 1)) * ease(clamp((q.e + 400 - t) / CAP_FADE, 0, 1)) : 0;
  api.set(el.cap, {opacity: f.toFixed(3)}); api.set(el.capBox, {opacity: (0.78 * f).toFixed(3)});
  intro(t, api);
}"""

SPEAKER_COLORS = ["#8fd3ff", "#ffb3d1", "#b8f28c", "#ffd27a"]


def build_scene(spec: dict, qid: str, avif: bytes, iw: int, ih: int, track: dict) -> dict:
    duration = int(math.ceil((track["track_ms"] + 300) / 100) * 100)
    who = list(dict.fromkeys(ln.get("who") for ln in spec["lines"] if ln.get("who")))
    head = {c["kind"]: c for c in track["cues"] if c.get("kind")}
    body = [c for c in track["cues"] if not c.get("kind")]
    cues = [{"t": c["t_ms"], "e": c["end_ms"], "text": c["text"], "who": ln.get("who", ""), "shot": ln["shot"], "tag": ln.get("tag", "")}
            for c, ln in zip(body, spec["lines"])]
    shots = list(spec["shots"]); intro = None
    if head:                                                             # the boxes fade out in the pause after the answer
        a = head["answer"]; intro = {"q": {"t": head["question"]["t_ms"], "text": spec["question"]["text"], "words": head["question"].get("words", [])},
                                     "a": {"t": a["t_ms"], "text": spec["answer"]["text"], "words": a.get("words", [])}, "out": a["end_ms"] + 350}
        shots.append({"x": iw / 2, "y": ih / 2, "z": 1})               # the whole picture behind the intro
    data = {"iw": iw, "ih": ih, "shots": shots, "cues": cues, "names": spec["names"], "intro": intro,
            "colors": {w: SPEAKER_COLORS[i % len(SPEAKER_COLORS)] for i, w in enumerate(who)}}
    font = 'font-family="system-ui, sans-serif"'
    intro_svg = ('<rect id="lesson-dim" x="0" y="0" width="%d" height="%d" fill="#0c0906" opacity="0"/>'
                 '<g id="lesson-q" opacity="0"><rect id="lesson-q-box" x="0" y="0" width="10" height="10" rx="18" fill="#fffaf0" stroke="#d9a441" stroke-width="3"/>'
                 '<rect id="lesson-q-hl" x="0" y="0" width="10" height="10" rx="9" fill="#ffd27a" opacity="0"/>'
                 '<text id="lesson-q-head" x="0" y="0" font-size="20" font-weight="800" letter-spacing="2" fill="#a86f12" %s>QUESTION</text>'
                 '<text id="lesson-q-text" text-anchor="middle" font-weight="700" fill="#1b2a4a" %s></text></g>'
                 '<g id="lesson-a" opacity="0"><rect id="lesson-a-box" x="0" y="0" width="10" height="10" rx="18" fill="#123d2a" stroke="#4fd18b" stroke-width="3"/>'
                 '<rect id="lesson-a-hl" x="0" y="0" width="10" height="10" rx="9" fill="#2f9e63" opacity="0"/>'
                 '<text id="lesson-a-head" x="0" y="0" font-size="20" font-weight="800" letter-spacing="2" fill="#7ee2a8" %s>ANSWER</text>'
                 '<text id="lesson-a-text" text-anchor="middle" font-weight="750" fill="#ffffff" %s></text></g>') % (W, H, font, font, font, font) if intro else ""
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg"><defs>'
           f'<radialGradient id="lesson-spot-g" gradientUnits="userSpaceOnUse" cx="480" cy="270" r="200">'
           f'<stop offset=".45" stop-color="#000" stop-opacity="0"/><stop offset=".72" stop-color="#0c0906" stop-opacity=".55"/><stop offset="1" stop-color="#0c0906" stop-opacity=".8"/></radialGradient>'
           f'<radialGradient id="lesson-vig" cx=".5" cy=".5" r=".75"><stop offset=".62" stop-color="#000" stop-opacity="0"/>'
           f'<stop offset="1" stop-color="#000" stop-opacity=".42"/></radialGradient></defs>'
           f'<image id="lesson-img" href="asset:img" x="0" y="0" width="{iw}" height="{ih}"/>'
           f'<rect id="lesson-spot" x="0" y="0" width="{W}" height="{H}" fill="url(#lesson-spot-g)" opacity="0"/>'
           f'<rect x="0" y="0" width="{W}" height="{H}" fill="url(#lesson-vig)"/>'
           f'<circle id="lesson-ring" cx="0" cy="0" r="10" fill="none" stroke="#f0c46a" stroke-width="2.5" opacity="0"/>'
           f'{intro_svg}'
           f'<g id="lesson-tag" opacity="0"><rect id="lesson-tag-box" x="22" y="20" width="200" height="40" rx="20" fill="#d9a441"/>'
           f'<text id="lesson-tag-text" x="36" y="47" font-size="22" font-weight="750" fill="#1f1a14" font-family="system-ui, sans-serif"></text></g>'
           f'<rect id="lesson-cap-box" x="{W*0.05:.0f}" y="440" width="{W*0.9:.0f}" height="60" rx="14" fill="#140f0a" opacity="0"/>'
           f'<text id="lesson-cap" x="{W/2:.0f}" y="480" text-anchor="middle" font-size="34" font-weight="700" fill="#fff" '
           f'font-family="system-ui, sans-serif"></text></svg>')
    return {"schema_version": 2, "qid": qid, "duration_ms": duration, "takeaway": spec["takeaway"],
            "stage": {"width": W, "height": H, "background": "#000000"},
            "assets": {"img": "data:image/avif;base64," + base64.b64encode(avif).decode("ascii")},
            "svg": svg, "script": SCRIPT.replace("__LESSON__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))}


def build_lesson(workspace: Path, qid: str) -> dict:
    """lessons/<QID>.lesson.json -> scenes/<QID>.scene.json + voice/<QID>.opus/.track.json; selection.json gets the real length."""
    src = workspace / "lessons" / f"{qid}.lesson.json"
    spec = check_lesson(json.loads(src.read_text(encoding="utf-8")), qid)
    img = (src.parent / spec["image"]).resolve()
    if not img.is_file(): _fail(f"image not found: {img}")
    avif, iw, ih = encode_avif(img)
    sx = iw / _image_size(img)[0]                                        # shots are written in the original image's pixels
    spec["shots"] = [{**s, "x": s["x"] * sx, "y": s["y"] * sx, **({"spot": [v * sx for v in s["spot"]]} if s.get("spot") else {})} for s in spec["shots"]]
    track = build_voice(spec, workspace / "voice", qid)
    scene = build_scene(spec, qid, avif, iw, ih, track)
    old = workspace / "scenes" / f"{qid}.scene.json"                      # keep the replace intent set by scaffold --replace
    if old.is_file() and json.loads(old.read_text(encoding="utf-8")).get("replace") is True: scene["replace"] = True
    (workspace / "scenes" / f"{qid}.scene.json").write_text(json.dumps(scene, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    sel_path = workspace / "selection.json"; sel = json.loads(sel_path.read_text(encoding="utf-8"))
    for row in sel["selected"]:
        if row["qid"] == qid: row["duration_ms"] = scene["duration_ms"]
    sel_path.write_text(json.dumps(sel, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"qid": qid, "duration_ms": scene["duration_ms"], "image_bytes": len(avif), "voice_bytes": track["bytes"], "lines": len(track["cues"])}


def _image_size(p: Path) -> tuple[int, int]:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    try: w, h = (int(v) for v in r.stdout.strip().split(",")[:2])
    except ValueError: _fail(f"cannot read the image size of {p.name}")
    return w, h
