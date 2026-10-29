// Data-ish detail blocks that sit inside a World: activity-threshold bars (CCS / NYHA classes) and a 24-hour dose strip.
// Each block returns its element plus small `in(t)` style methods that schedule animation at absolute times.

import { h } from './dom.js';
import { toneVar } from './components.js';

/**
 * Functional-class bars. Every row is a bar over an activity axis (rest → strenuous): the teal part is where the patient
 * is symptom-free, the pink part where symptoms start; the marker sits on the threshold. Class I has a high threshold,
 * class IV a very low one, so the "limitation" the book describes becomes a distance the viewer can see.
 *
 *   rows: [{ numeral: 'I', text: 'No angina with ordinary activity', thr: 0.84 }, …]
 */
export function thresholdBars(R, { w = 900, rowH = 190, rows, axis = [['Rest', 0], ['Minimal', 0.26], ['Ordinary', 0.6], ['Strenuous', 1]], guide = 0.6, guideLabel = 'ordinary activity', numW = 150 }) {
  const bw = w - numW;
  const height = rows.length * rowH + 96;
  const el = h('div', { class: 'tb', style: { width: `${w}px`, height: `${height}px` } });

  const guideEl = h('div', { class: 'tb-guide', style: { left: `${numW + guide * bw}px`, height: `${rows.length * rowH - 20}px` } }, h('span', {}, guideLabel));
  el.append(guideEl);
  R.chan(guideEl, 'opacity').initial = 0;

  const out = rows.map((r, i) => {
    const num = h('div', { class: 'tb-num', style: { '--tone': toneVar(r.tone ?? 'neutral') } }, r.numeral);
    const free = h('i', { class: 'tb-free' });
    const sym = h('i', { class: 'tb-sym' });
    const mark = h('b', { class: 'tb-mark', style: { left: `${r.thr * bw - 17}px` } });
    const bar = h('div', { class: 'tb-bar' }, free, sym, mark);
    const desc = h('div', { class: 'tb-desc' }, r.text);
    const row = h('div', { class: 'tb-row', style: { top: `${i * rowH}px`, '--hl': 0 } }, num, h('div', { class: 'tb-body' }, bar, desc));
    el.append(row);
    const thr = r.thr * bw;
    R.chan(free, 'css:width', { initial: 0, unit: 'px' });
    R.chan(sym, 'css:width', { initial: 0, unit: 'px' });
    sym.style.left = `${thr}px`;
    R.chan(row, 'css:--hl', { initial: 0 });
    for (const e of [row, mark]) R.chan(e, 'opacity').initial = 0;
    return {
      el: row, numEl: num, descEl: desc, markEl: mark, thr,
      /** Row appears (numeral and bar track). */
      in(t) { R.show(row, t, { dur: 0.6, y: 24 }); return this; },
      /** The symptom-free zone grows, then the symptom zone, then the marker pops. */
      fill(t) {
        R.tween(free, t, 0.7, { 'css:width': thr }, { ease: 'outCubic' });
        R.tween(sym, t + 0.45, 0.6, { 'css:width': bw - thr }, { ease: 'outCubic' });
        R.show(mark, t + 0.55, { dur: 0.5, y: 0, scale: 0.3, ease: 'outSoft' });
        return this;
      },
      hl(t, v = 1, dur = 0.4) { R.tween(row, t, dur, { 'css:--hl': v }, { ease: 'outCubic' }); return this; },
    };
  });

  // axis
  const axisEl = h('div', { class: 'tb-axis', style: { top: `${rows.length * rowH + 8}px`, left: `${numW}px`, width: `${bw}px` } },
    ...axis.map(([label, f], k) => h('span', { class: ['tb-tick', k === 0 && 'first', k === axis.length - 1 && 'last'], style: { left: `${f * bw}px` } }, label)));
  el.append(axisEl);
  R.chan(axisEl, 'opacity').initial = 0;

  return {
    el, rows: out, height,
    axisIn(t) { R.show(axisEl, t, { dur: 0.6, y: 12 }); R.show(guideEl, t + 0.1, { dur: 0.6, y: 0 }); return this; },
  };
}

/** A 24-hour strip with spray/dose dots that pop one after another and a running counter. */
export function dayStrip(R, { w = 900, doses = [], icon = 'spray-can', tone = 'violet', label = '×' }) {
  const el = h('div', { class: 'ds', style: { width: `${w}px`, '--tone': toneVar(tone) } });
  const track = h('div', { class: 'ds-track' });
  const ticks = [0, 6, 12, 18, 24].map((hr) => h('span', { class: 'ds-tick', style: { left: `${(hr / 24) * w}px` } }, `${String(hr).padStart(2, '0')}h`));
  const count = h('div', { class: 'ds-count' }, h('span', { class: 'x' }, label), h('b', {}, '0'));
  el.append(count, track, ...ticks);
  const pins = doses.map((hr, i) => {
    const pin = h('div', { class: 'ds-pin', style: { left: `${(hr / 24) * w}px` } }, R.icon(icon, { size: 76, stroke: 1.7 }), h('i', {}));
    el.append(pin);
    R.chan(pin, 'opacity').initial = 0;
    return pin;
  });
  return {
    el, pins,
    /** Pin i pops at t and the counter ticks up. */
    dose(i, t) {
      R.show(pins[i], t, { dur: 0.5, y: -26, scale: 0.6, ease: 'outSoft' });
      R.fn(t, t + 0.01, () => { count.querySelector('b').textContent = String(i + 1); });
      // keep the counter a pure function of time: show the number of pins popped so far
      return this;
    },
    counter(times) {
      R.fn(0, R.duration, (_p, T) => { count.querySelector('b').textContent = String(times.filter((x) => T >= x).length); });
      return this;
    },
  };
}
