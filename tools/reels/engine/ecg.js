// ECG strips: scrolling traces drawn from a list of R-peak times. Everything is a pure function of the reel time, so
// a strip can be sampled at any frame. Rhythms are described by a rate function (beats per minute over reel time).
//
//   const bs = beats((t) => (t > 24 && t < 25.2 ? 168 : 72));        // paroxysmal burst
//   const strip = ecgStrip(R, { w: 880, h: 160, bs, tone: 'pink' });  // → { el, rate(fn), in(t) }
//   W.put(strip.el, { x: 100, y: 800, anchor: 'tl' });  strip.in(t);

import { h } from './dom.js';
import { clamp } from './core.js';
import { toneVar } from './components.js';

/** Small seeded PRNG (mulberry32) for repeatable "irregular" rhythms. */
export function rng(seed) {
  let a = seed | 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * R-peak times for a time-varying rate (bpm). `jitter` is the random spread of each interval (fraction of the interval),
 * `omit` removes beats near the given times ("skipped beats").
 */
export function beats(rate, { from = -6, to = 66, jitter = 0, seed = 1, omit = [] } = {}) {
  const rnd = rng(seed);
  const next = () => 1 + (jitter ? (rnd() - 0.5) * 2 * jitter : 0);
  const out = [];
  let phase = rnd() * 0.6, need = next();
  const dt = 0.002;
  for (let t = from; t < to; t += dt) {
    phase += (rate(t) / 60) * dt;
    if (phase >= need) { out.push(t); phase = 0; need = next(); }
  }
  return omit.length ? out.filter((b) => !omit.some((o) => Math.abs(b - o) < 0.3)) : out;
}

const gauss = (x, mu, sig, a) => a * Math.exp(-0.5 * ((x - mu) / sig) ** 2);

function lowerBound(a, x) { let lo = 0, hi = a.length; while (lo < hi) { const m = (lo + hi) >> 1; if (a[m] < x) lo = m + 1; else hi = m; } return lo; }

/** Trace value at time t (≈ −0.35 … 1): P, Q, R, S, T waves around every R peak; `fib` swaps P waves for fibrillatory baseline. */
export function ecgAt(t, bs, { p = true, fib = false } = {}) {
  let v = 0;
  const i0 = Math.max(0, lowerBound(bs, t - 0.7) - 1), i1 = Math.min(bs.length, lowerBound(bs, t + 0.4) + 1);
  for (let i = i0; i < i1; i++) {
    const prev = i ? bs[i] - bs[i - 1] : 0.85;
    const sc = clamp(prev / 0.85, 0.5, 1);
    const x = t - bs[i];
    v += gauss(x, -0.035, 0.007, -0.1) + gauss(x, 0, 0.0095, 1) + gauss(x, 0.032, 0.0095, -0.24) + gauss(x, 0.08 + 0.2 * sc, 0.045 * sc + 0.012, 0.3);
    if (p && !fib) v += gauss(x, -0.13 - 0.04 * sc, 0.026, 0.12);
  }
  if (fib) v += 0.035 * Math.sin(2 * Math.PI * 5.7 * t) + 0.025 * Math.sin(2 * Math.PI * 7.9 * t + 1.3) + 0.02 * Math.sin(2 * Math.PI * 10.3 * t + 0.4);
  return v;
}

/**
 * Scrolling strip. The newest sample is at the right edge; older ones fade out to the left.
 * Returns { el, in(t), rate(bpmFn, el) } — `rate` keeps a number element in step with the rhythm (e.g. a big "bpm" readout).
 */
export function ecgStrip(R, { w = 880, h: hh = 160, window = 4.5, bs, tone = 'teal', p = true, fib = false, t0 = 0, t1 = R.duration, grid = true, id = `ecg${Math.random().toString(36).slice(2, 7)}` }) {
  const base = hh * 0.7, amp = hh * 0.58;
  const svg = h('svg', { class: 'ecg', width: w, height: hh, viewBox: `0 0 ${w} ${hh}`, style: { '--tone': toneVar(tone) } },
    h('defs', {},
      h('linearGradient', { id: `${id}g`, gradientUnits: 'userSpaceOnUse', x1: 0, y1: 0, x2: w, y2: 0 },
        h('stop', { offset: '0', 'stop-color': 'currentColor', 'stop-opacity': 0 }), h('stop', { offset: '0.35', 'stop-color': 'currentColor', 'stop-opacity': 0.55 }), h('stop', { offset: '1', 'stop-color': 'currentColor', 'stop-opacity': 1 })),
      h('pattern', { id: `${id}p`, width: 22, height: 22, patternUnits: 'userSpaceOnUse' }, h('path', { d: 'M22 0H0V22', fill: 'none', stroke: '#fff', 'stroke-opacity': 0.06, 'stroke-width': 1 }))),
    grid ? h('rect', { x: 0, y: 0, width: w, height: hh, rx: 22, fill: `url(#${id}p)`, stroke: 'rgba(255,255,255,.1)', 'stroke-width': 1.5 }) : null,
    h('path', { class: 'ecg-line', stroke: `url(#${id}g)` }),
    h('circle', { class: 'ecg-dot', r: 7 }));
  svg.style.color = toneVar(tone);
  const line = svg.querySelector('.ecg-line'), dot = svg.querySelector('.ecg-dot');
  const N = Math.round(w / 2.5);
  R.chan(svg, 'opacity').initial = 0;
  R.fn(t0, t1, (_p, s) => {
    const T = t0 + s;
    let d = '', y = base;
    for (let k = 0; k <= N; k++) {
      const x = (w * k) / N;
      y = base - ecgAt(T - window + (window * k) / N, bs, { p, fib }) * amp;
      d += `${k ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`;
    }
    line.setAttribute('d', d);
    dot.setAttribute('cx', w - 2); dot.setAttribute('cy', y.toFixed(1));
  });
  return {
    el: svg,
    in(t) { R.show(svg, t, { dur: 0.6, y: 18 }); return this; },
    /** Keep `el`'s text equal to the rhythm's rate (rounded bpm) at every frame. */
    rate(bpm, el, { from = 0, to = R.duration } = {}) {
      R.fn(from, to, (_p, s) => { el.textContent = String(Math.round(bpm(from + s))); });
      return this;
    },
  };
}
