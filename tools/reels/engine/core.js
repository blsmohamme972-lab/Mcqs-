// Pure, DOM-free building blocks: easing, keyframe channels, script tokenizing and timing layout.
// Everything here is a deterministic function of its inputs, so frames can be rendered in any order
// (or in parallel) and unit-tested in Node.

export const clamp = (x, a = 0, b = 1) => (x < a ? a : x > b ? b : x);
export const lerp = (a, b, t) => a + (b - a) * t;

/** CSS-style cubic-bezier easing (Newton-Raphson with a bisection fallback). */
export function bezier(x1, y1, x2, y2) {
  const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
  const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
  const sx = (t) => ((ax * t + bx) * t + cx) * t;
  const sy = (t) => ((ay * t + by) * t + cy) * t;
  const dx = (t) => (3 * ax * t + 2 * bx) * t + cx;
  return (x) => {
    if (x <= 0) return 0;
    if (x >= 1) return 1;
    let t = x;
    for (let i = 0; i < 8; i++) {
      const err = sx(t) - x;
      if (Math.abs(err) < 1e-6) return sy(t);
      const d = dx(t);
      if (Math.abs(d) < 1e-6) break;
      t -= err / d;
    }
    let lo = 0, hi = 1;
    t = x;
    while (lo < hi) {
      const v = sx(t);
      if (Math.abs(v - x) < 1e-6) break;
      if (x > v) lo = t; else hi = t;
      t = (hi - lo) / 2 + lo;
      if (hi - lo < 1e-7) break;
    }
    return sy(t);
  };
}

const pow = (n) => ({ in: (t) => t ** n, out: (t) => 1 - (1 - t) ** n, inOut: (t) => (t < 0.5 ? 2 ** (n - 1) * t ** n : 1 - (-2 * t + 2) ** n / 2) });
const quad = pow(2), cubic = pow(3), quart = pow(4), quint = pow(5);
const C1 = 1.70158;

export const ease = {
  linear: (t) => t,
  inSine: (t) => 1 - Math.cos((t * Math.PI) / 2),
  outSine: (t) => Math.sin((t * Math.PI) / 2),
  inOutSine: (t) => -(Math.cos(Math.PI * t) - 1) / 2,
  inQuad: quad.in, outQuad: quad.out, inOutQuad: quad.inOut,
  inCubic: cubic.in, outCubic: cubic.out, inOutCubic: cubic.inOut,
  inQuart: quart.in, outQuart: quart.out, inOutQuart: quart.inOut,
  inQuint: quint.in, outQuint: quint.out, inOutQuint: quint.inOut,
  inExpo: (t) => (t <= 0 ? 0 : 2 ** (10 * t - 10)),
  outExpo: (t) => (t >= 1 ? 1 : 1 - 2 ** (-10 * t)),
  inOutExpo: (t) => (t <= 0 ? 0 : t >= 1 ? 1 : t < 0.5 ? 2 ** (20 * t - 10) / 2 : (2 - 2 ** (-20 * t + 10)) / 2),
  inBack: (t) => (C1 + 1) * t ** 3 - C1 * t ** 2,
  outBack: (t) => 1 + (C1 + 1) * (t - 1) ** 3 + C1 * (t - 1) ** 2,
  inOutBack: (t) => { const c = C1 * 1.525; return t < 0.5 ? ((2 * t) ** 2 * ((c + 1) * 2 * t - c)) / 2 : ((2 * t - 2) ** 2 * ((c + 1) * (t * 2 - 2) + c) + 2) / 2; },
  // Soft overshoot (~8%) that settles by t = 1: the default "pop".
  outSoft: (t) => 1 + 2.4 * (t - 1) ** 3 + 1.4 * (t - 1) ** 2,
  // Material-style standard / emphasised curves.
  standard: bezier(0.2, 0, 0, 1),
  emphasized: bezier(0.05, 0.7, 0.1, 1),
};

export function easeFn(spec = 'outCubic') {
  if (typeof spec === 'function') return spec;
  if (Array.isArray(spec)) return bezier(...spec);
  const f = ease[spec];
  if (!f) throw new Error(`unknown easing "${spec}"`);
  return f;
}

/**
 * A numeric value over time built from segments. Segment i eases from the value reached by the
 * previous segment (or an explicit `from`) to `to`. Insertion order does not matter, and the value
 * at any time T is independent of which times were evaluated before, so seeking is exact.
 */
export class Channel {
  constructor(initial = 0) {
    this.initial = initial;
    this.segs = [];
    this.dirty = false;
  }

  to(t0, dur, to, { ease: e = 'outCubic', from } = {}) {
    this.segs.push({ t0, t1: t0 + Math.max(dur, 1e-6), to, from, ease: easeFn(e), f: 0 });
    this.dirty = true;
    return this;
  }

  set(t0, v) { return this.to(t0, 0, v); }

  _resolve() {
    this.segs.sort((a, b) => a.t0 - b.t0);
    this.segs.forEach((g, i) => {
      g.f = g.from ?? (i === 0 ? this.initial : this._segValue(i - 1, g.t0));
    });
    this.dirty = false;
  }

  _segValue(i, T) {
    const g = this.segs[i];
    if (T >= g.t1) return g.to;
    return lerp(g.f, g.to, g.ease((T - g.t0) / (g.t1 - g.t0)));
  }

  at(T) {
    if (this.dirty) this._resolve();
    const s = this.segs;
    let lo = 0, hi = s.length - 1, i = -1;
    while (lo <= hi) {
      const m = (lo + hi) >> 1;
      if (s[m].t0 <= T) { i = m; lo = m + 1; } else hi = m - 1;
    }
    return i < 0 ? this.initial : this._segValue(i, T);
  }

  get end() { return this.segs.reduce((m, g) => Math.max(m, g.t1), 0); }
}

// ---------------------------------------------------------------------------------------------
// Script tokenizing and timing layout
// ---------------------------------------------------------------------------------------------

/** Heuristic English syllable count; only used to apportion time before real audio exists. */
export function syllables(word) {
  let w = word.toLowerCase().replace(/[^a-z]/g, '');
  if (!w) return 0;
  if (w.length <= 3) return 1;
  w = w.replace(/(?:[^laeiouy]es|ed|[^laeiouy]e)$/, '').replace(/^y/, '');
  const m = w.match(/[aeiouy]{1,2}/g);
  return Math.max(1, m ? m.length : 1);
}

export const normWord = (w) => w.toLowerCase().replace(/[^a-z0-9α-ωµ°]+/g, '');

/**
 * Parse one script sentence.
 *   "Class {III=three} and {IV=four} / carry more risk."
 * `/` separates caption phrases (one phrase on screen at a time).
 * `{shown=spoken}` shows one thing and speaks another (numerals, acronyms, Roman numerals).
 */
export function parseSentence(text) {
  const phrases = text.split(/\s+\/\s+/).map((p) => p.trim()).filter(Boolean);
  let idx = 0;
  return phrases.map((p) => ({
    // A token is either a {shown=spoken} group (the spoken part may contain spaces) or a run of non-space characters.
    words: (p.match(/\{[^}]+\}[.,;:!?]*|[^\s{]+/g) ?? []).map((tok) => {
      const m = tok.match(/^\{(.+?)=(.+)\}([.,;:!?]*)$/);
      const shown = m ? m[1] + m[3] : tok;
      const spoken = m ? m[2] : tok;
      return { shown, spoken, key: normWord(shown), index: idx++ };
    }),
  }));
}

export const plainText = (text) => parseSentence(text).flatMap((p) => p.words.map((w) => w.shown)).join(' ');
export const spokenText = (text) => parseSentence(text).flatMap((p) => p.words.map((w) => w.spoken)).join(' ');

const PUNCT_PAUSE = [[/[.!?]$/, 0.3], [/[:;]$/, 0.22], [/,$/, 0.16], [/[—–]$/, 0.14]];

function wordSeconds(w) {
  const syl = w.spoken.split(/[\s-]+/).reduce((n, part) => n + syllables(part), 0) || 1;
  return 0.06 + 0.2 * syl;
}

/** Estimated (unscaled) speech time for each word of a parsed sentence, in seconds. */
export function estimateWords(parsed) {
  const words = parsed.flatMap((p, pi) => p.words.map((w, wi) => ({ ...w, phrase: pi, last: wi === p.words.length - 1 })));
  return words.map((w, i) => {
    // The pause after the sentence's final word is the gap between sentences, not part of the speech.
    if (i === words.length - 1) return { ...w, dur: wordSeconds(w), pause: 0 };
    let pause = 0;
    for (const [re, sec] of PUNCT_PAUSE) if (re.test(w.shown)) { pause = sec; break; }
    if (!pause && w.last) pause = 0.12; // phrase break
    return { ...w, dur: wordSeconds(w), pause };
  });
}

/**
 * Lay the sentences of a script on a timeline of exactly `duration` seconds.
 *
 * Without audio, speech time is estimated and scaled by one global factor so the narration fills
 * the reel. With audio (`audioDurations[id]` in seconds) the real lengths are used and only the gaps
 * flex, so visuals stay glued to the voice whichever TTS engine produced it.
 */
export function layoutTimeline(script, { duration = 60, lead = 0.6, tail = 2.0, gap = 0.35, audioDurations = null } = {}) {
  const items = script.sentences.map((s) => {
    const parsed = parseSentence(s.text);
    const words = estimateWords(parsed);
    const raw = words.reduce((n, w) => n + w.dur + w.pause, 0);
    const audio = audioDurations?.[s.id] ?? null;
    return { s, parsed, words, raw, audio, pause: s.pause ?? gap };
  });
  const gaps = items.reduce((n, it, i) => n + (i < items.length - 1 ? it.pause : 0), 0);
  const speech = items.reduce((n, it) => n + (it.audio ?? it.raw), 0);
  const avail = duration - lead - tail;
  let k = 1, gapScale = 1;
  const usingAudio = items.every((it) => it.audio != null);
  if (usingAudio) {
    gapScale = clamp((avail - speech) / Math.max(gaps, 1e-6), 0, 2.5);
    if (speech > avail) throw new Error(`narration (${speech.toFixed(1)} s) is longer than the ${avail.toFixed(1)} s available`);
  } else {
    k = (avail - gaps) / speech;
  }
  let t = lead;
  const sentences = items.map((it, si) => {
    const dur = usingAudio ? it.audio : it.raw * k;
    const start = t;
    const unit = dur / it.raw;
    let wt = start;
    const words = it.words.map((w) => {
      const d = w.dur * unit;
      const o = { shown: w.shown, spoken: w.spoken, key: w.key, index: w.index, phrase: w.phrase, start: wt, end: wt + d };
      wt += d + w.pause * unit;
      return o;
    });
    const phrases = [];
    for (const w of words) (phrases[w.phrase] ??= { start: w.start, end: w.end, words: [] }, phrases[w.phrase].end = w.end, phrases[w.phrase].words.push(w));
    t = start + dur + (si < items.length - 1 ? it.pause * gapScale : 0);
    return { id: it.s.id, text: it.s.text, start, end: start + dur, dur, words, phrases };
  });
  const words = sentences.reduce((n, s) => n + s.words.length, 0);
  return { duration, lead, tail, sentences, meta: { words, speechSeconds: speech * (usingAudio ? 1 : k), k, usingAudio, endsAt: t } };
}
