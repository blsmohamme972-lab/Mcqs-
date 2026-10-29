// Reusable reel components. Each takes the Reel runtime `R` first and schedules its own animation
// at absolute times, so a reel reads as a list of "what appears when the narrator says it".

import { h } from './dom.js';

/** Tone → CSS colour variable (categorical tones are the validated trio; the rest are neutral). */
export const TONE = {
  pink: 'var(--pink)', teal: 'var(--teal)', violet: 'var(--violet)',
  pinkT: 'var(--pink-t)', tealT: 'var(--teal-t)', violetT: 'var(--violet-t)',
  good: 'var(--good)', warn: 'var(--warn)', serious: 'var(--serious)', crit: 'var(--crit)',
  neutral: 'var(--t2)', white: 'var(--t1)',
};
export const toneVar = (t) => TONE[t] ?? t;

/**
 * Headline with word-level reveal. `*word words*` renders as italic gradient serif.
 * Returns { el, words, reveal(t, step, opts) }.
 */
export function rich(R, text, { cls = 'serif m', style = {}, tag = 'div' } = {}) {
  const el = h(tag, { class: ['rich', cls], style });
  const words = [];
  const parts = text.split(/(\*[^*]+\*)/).filter(Boolean);
  for (const part of parts) {
    const em = part.startsWith('*');
    for (const w of (em ? part.slice(1, -1) : part).split(/\s+/).filter(Boolean)) {
      const span = h('span', { class: ['wd', em && 'em grad'] }, w);
      words.push(span);
      el.append(span, ' ');
    }
  }
  return {
    el, words,
    /** Reveal all words, `step` seconds apart, starting at t. Pass an array of times to cue each word instead. */
    reveal(t, step = 0.08, opts = {}) {
      words.forEach((w, i) => R.show(w, Array.isArray(t) ? t[i] : t + i * step, { dur: 0.7, y: 34, blur: 10, ...opts }));
    },
  };
}

/** Small mono caps label with an optional coloured dot. */
export function eyebrow(R, text, { x = 72, y = 230, tone, w } = {}) {
  return h('div', { class: 'eyebrow', style: { left: `${x}px`, top: `${y}px`, ...(w ? { width: `${w}px` } : {}) } },
    tone ? h('i', { class: 'edot', style: { background: toneVar(tone) } }) : null, text);
}

/**
 * Icon tile. `lit` drives a glow in the tone colour (css var --lit, 0→1).
 *   layout 'col': icon above label (bedside/step tiles)   'row': icon left of label
 */
export function tile(R, { icon, label, sub, tone = 'neutral', x, y, w, hgt, layout = 'col', iconSize = 64, labelSize }) {
  const el = h('div', { class: ['tile', `tile-${layout}`], style: { left: `${x}px`, top: `${y}px`, width: `${w}px`, height: `${hgt}px`, '--tone': toneVar(tone), '--lit': 0 } },
    h('div', { class: 'tile-ic' }, R.icon(icon, { size: iconSize, stroke: 1.6 })),
    h('div', { class: 'tile-tx' }, h('div', { class: 'tile-lb', style: labelSize ? { fontSize: `${labelSize}px` } : {} }, label), sub ? h('div', { class: 'tile-sub' }, sub) : null));
  R.chan(el, 'css:--lit', { initial: 0 });
  return {
    el,
    lit(t, on = true, dur = 0.35) { R.tween(el, t, dur, { 'css:--lit': on ? 1 : 0 }, { ease: 'outCubic' }); return this; },
  };
}

/** Animated underline that sweeps under an element's width (element must be position:relative/absolute). */
export function underline(R, host, t, { dur = 0.5, color = 'var(--accent)', thickness = 6, offset = -10 } = {}) {
  const u = h('i', { class: 'uline', style: { background: color, height: `${thickness}px`, bottom: `${offset}px` } });
  host.append(u);
  R.chan(u, 'css:--w', { initial: 0 });
  R.tween(u, t, dur, { 'css:--w': 1 }, { ease: 'outExpo' });
  return u;
}

/** Stroke-draw an SVG path between t and t+dur. */
export function drawPath(R, path, t, dur = 0.8, { ease = 'inOutCubic' } = {}) {
  let len = 0;
  R.fn(t, t + dur, (p) => {
    if (!len) { len = path.getTotalLength(); path.style.strokeDasharray = `${len} ${len}`; }
    path.style.strokeDashoffset = `${len * (1 - p)}`;
  }, { ease });
}

/** Count a number up (or down) with a formatter. */
export function counter(R, el, t, dur, from, to, fmt = (v) => Math.round(v)) {
  R.fn(t, t + dur, (p) => { el.textContent = fmt(from + (to - from) * p); }, { ease: 'outExpo' });
}

/** Rounded status badge: icon + label, never colour alone (status palette is reserved). */
export function status(R, kind, label, { size = 34 } = {}) {
  const map = { good: ['check', 'good'], warn: ['circle-help', 'warn'], serious: ['triangle-alert', 'serious'], crit: ['octagon-x', 'crit'], stop: ['octagon-x', 'crit'] };
  const [ic, tone] = map[kind];
  return h('span', { class: 'status', style: { '--tone': toneVar(tone), fontSize: `${size}px` } }, R.icon(ic, { size: size * 1.05, stroke: 2.4 }), label);
}
