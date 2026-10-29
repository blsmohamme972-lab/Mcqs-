// Browser layer. Import-safe in Node (nothing touches `document` at load time).
// A reel is a pure function of time: `reel.render(T)` sets every element from its channels.

import { Channel, clamp, easeFn, normWord } from './core.js';

const SVG_NS = 'http://www.w3.org/2000/svg';
const SVG_TAGS = new Set(['svg', 'g', 'path', 'circle', 'ellipse', 'rect', 'line', 'polyline', 'polygon', 'text', 'tspan', 'defs', 'linearGradient', 'radialGradient', 'stop', 'clipPath', 'mask', 'filter', 'feGaussianBlur', 'feColorMatrix', 'feMerge', 'feMergeNode', 'feOffset', 'feFlood', 'feComposite', 'use', 'symbol', 'marker', 'pattern']);

/** Hyperscript: h('div', {class:'card', style:{left:'72px'}}, 'text', child…). Creates SVG elements for SVG tags. */
export function h(tag, props = {}, ...children) {
  const el = SVG_TAGS.has(tag) ? document.createElementNS(SVG_NS, tag) : document.createElement(tag);
  for (const [k, v] of Object.entries(props ?? {})) {
    if (v == null || v === false) continue;
    if (k === 'class') el.setAttribute('class', Array.isArray(v) ? v.filter(Boolean).join(' ') : v);
    else if (k === 'style') {
      if (typeof v === 'string') el.setAttribute('style', v);
      else for (const [sk, sv] of Object.entries(v)) (sk.startsWith('--') ? el.style.setProperty(sk, sv) : (el.style[sk] = sv));
    } else if (k === 'html') el.innerHTML = v;
    else el.setAttribute(k, v === true ? '' : String(v));
  }
  for (const c of children.flat(Infinity)) if (c != null && c !== false) el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  return el;
}

/** One narrated sentence with word-level timing and cue lookup. */
export class Sent {
  constructor(s) {
    Object.assign(this, s);
  }

  /** Start time of a word (or consecutive words, "cold air"). `n` picks the n-th occurrence. */
  at(key, n = 1) { return this._find(key, n).start; }
  /** End time of the last word of `key`. */
  endOf(key, n = 1) { return this._find(key, n, true).end; }
  rel(sec) { return this.start + sec; }
  frac(f) { return this.start + f * this.dur; }

  _find(key, n, last = false) {
    const parts = String(key).split(/\s+/).map(normWord);
    let seen = 0;
    for (let i = 0; i + parts.length <= this.words.length; i++) {
      if (parts.every((p, j) => this.words[i + j].key === p) && ++seen === n) return this.words[last ? i + parts.length - 1 : i];
    }
    throw new Error(`cue "${key}" (#${n}) not found in sentence "${this.id}": ${this.text}`);
  }
}

const DEFAULTS = { opacity: 1, x: 0, y: 0, scale: 1, sx: 1, sy: 1, rot: 0, blur: 0 };
const TRANSFORM = ['x', 'y', 'rot', 'scale', 'sx', 'sy'];

export class Reel {
  constructor({ stage, timing, icons = {}, meta = {} }) {
    this.stage = stage;
    this.timing = timing;
    this.icons = icons;
    this.meta = meta;
    this.duration = timing.duration;
    this.items = new Map(); // Element → { ch: {name: Channel}, last: {} }
    this.fns = [];
    this.s = Object.fromEntries(timing.sentences.map((s) => [s.id, new Sent(s)]));
    this.h = h;
    stage.replaceChildren();
    this.layers = {};
    for (const name of ['bg', 'scenes', 'hud', 'captions', 'fx']) {
      this.layers[name] = h('div', { class: `layer layer-${name}` });
      stage.append(this.layers[name]);
    }
  }

  // ------------------------------------------------------------------ channels
  chan(el, name, { initial, unit } = {}) {
    let st = this.items.get(el);
    if (!st) this.items.set(el, (st = { ch: {}, last: {}, unit: {} }));
    if (!st.ch[name]) {
      st.ch[name] = new Channel(initial ?? DEFAULTS[name] ?? 0);
      if (unit) st.unit[name] = unit;
    }
    return st.ch[name];
  }

  /** Tween any mix of: opacity x y scale sx sy rot blur, "css:--var", "attr:name". */
  tween(el, t, dur, props, { ease = 'outCubic', from = {}, unit } = {}) {
    for (const [name, to] of Object.entries(props)) {
      const ch = this.chan(el, name, { initial: from[name], unit: unit?.[name] });
      ch.to(t, dur, to, { ease, from: from[name] });
    }
    return el;
  }

  /** Fade/slide an element in. Before `t` it rests at the "from" pose, so it is invisible until cued. */
  show(el, t, { dur = 0.55, x = 0, y = 36, scale = 1, blur = 0, ease = 'outExpo', delay = 0 } = {}) {
    const from = { opacity: 0, x, y, scale, blur };
    for (const [name, v] of Object.entries(from)) {
      const ch = this.chan(el, name);
      if (!ch.segs.length) ch.initial = v;
    }
    return this.tween(el, t + delay, dur, { opacity: 1, x: 0, y: 0, scale: 1, blur: 0 }, { ease, from });
  }

  hide(el, t, { dur = 0.35, x = 0, y = -20, scale = 1, blur = 0, ease = 'inCubic' } = {}) {
    return this.tween(el, t, dur, { opacity: 0, x, y, scale, blur }, { ease });
  }

  /** Call `cb(progress, localSeconds)` every frame; clamps to 0 before and 1 after, so rest states are exact. */
  fn(t0, t1, cb, { ease = 'linear' } = {}) {
    this.fns.push({ t0, t1, cb, ease: easeFn(ease), last: NaN });
  }

  /** Reveal elements one after another. */
  stagger(els, t, step, cb) {
    els.forEach((el, i) => cb(el, i, t + i * step));
  }

  // ------------------------------------------------------------------ render
  render(T) {
    for (const [el, st] of this.items) {
      const c = st.ch, v = {};
      let moved = false;
      for (const name in c) {
        v[name] = c[name].at(T);
        if (v[name] !== st.last[name]) { st.last[name] = v[name]; moved = true; }
      }
      if (!moved) continue;
      if (c.opacity) {
        el.style.opacity = v.opacity;
        el.style.visibility = v.opacity <= 0.002 ? 'hidden' : 'visible';
      }
      if (TRANSFORM.some((n) => c[n])) {
        const g = (n) => v[n] ?? DEFAULTS[n];
        const sc = g('scale');
        // CSS transforms need units even on SVG children (unitless values are silently dropped).
        el.style.transform = `translate(${g('x')}px, ${g('y')}px) rotate(${g('rot')}deg) scale(${sc * g('sx')}, ${sc * g('sy')})`;
      }
      if (c.blur) el.style.filter = v.blur > 0.05 ? `blur(${v.blur}px)` : '';
      for (const name in c) {
        if (name.startsWith('css:')) el.style.setProperty(name.slice(4), `${v[name]}${st.unit[name] ?? ''}`);
        else if (name.startsWith('attr:')) el.setAttribute(name.slice(5), v[name]);
      }
    }
    for (const f of this.fns) {
      const p = f.t1 <= f.t0 ? (T >= f.t0 ? 1 : 0) : f.ease(clamp((T - f.t0) / (f.t1 - f.t0)));
      if (p !== f.last) { f.last = p; f.cb(p, clamp(T - f.t0, 0, Math.max(f.t1 - f.t0, 0))); }
    }
  }

  // ------------------------------------------------------------------ building blocks
  /** SVG icon (Lucide) at `size` px with a stroke thickness in viewBox units. */
  icon(name, { size = 64, stroke = 1.75, color } = {}) {
    const body = this.icons[name];
    if (!body) throw new Error(`unknown icon "${name}"`);
    return h('svg', { class: 'icon', viewBox: '0 0 24 24', width: size, height: size, fill: 'none', stroke: color ?? 'currentColor', 'stroke-width': stroke, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', html: body });
  }

  /**
   * A time-bounded full-frame container that fades in and out; `build(sc)` fills it.
   * Content sits on a "camera" layer that drifts a few percent over the scene for a touch of life.
   */
  scene(t0, t1, build, { enter = {}, exit = {}, name = '', drift = 0.022 } = {}) {
    const el = h('div', { class: 'scene', 'data-name': name });
    const cam = h('div', { class: 'cam' });
    el.append(cam);
    this.layers.scenes.append(el);
    this.show(el, t0, { dur: 0.5, y: 28, ...enter });
    if (exit !== false) this.hide(el, t1 - 0.32, { dur: 0.32, y: -22, ...exit });
    if (drift) this.fn(t0, t1, (p) => { cam.style.transform = `scale(${1 + drift * p})`; }, { ease: 'inOutSine' });
    const sc = { el, cam, t0, t1, R: this, add: (...n) => (cam.append(...n), n[0]) };
    build(sc);
    return sc;
  }

  /** Always-on header: topic kicker on the left, reel counter and book page on the right. */
  hud({ kicker, index, total, source }) {
    const pad = (n) => String(n).padStart(2, '0');
    const top = h('div', { class: 'hud-top' },
      h('div', { class: 'kicker' }, h('i', { class: 'kdot' }), kicker),
      h('div', { class: 'counter' }, h('span', {}, h('b', {}, pad(index)), ` / ${pad(total)}`), source ? h('span', { class: 'srcchip' }, source) : null));
    this.layers.hud.append(top);
    return top;
  }

  /** Ink background with slowly drifting glows and a faint grid. */
  background({ hueA = 'var(--violet)', hueB = 'var(--pink)' } = {}) {
    const a = h('div', { class: 'glow glow-a', style: { '--c': hueA } });
    const b = h('div', { class: 'glow glow-b', style: { '--c': hueB } });
    this.layers.bg.append(h('div', { class: 'grid' }), a, b);
    this.fn(0, this.duration, (_p, s) => {
      a.style.transform = `translate(${Math.sin(s * 0.21) * 46}px, ${Math.cos(s * 0.17) * 38}px)`;
      b.style.transform = `translate(${Math.cos(s * 0.19) * 52}px, ${Math.sin(s * 0.23) * 44}px)`;
    });
  }

  /**
   * Phrase-by-phrase captions. Each phrase of each sentence is one on-screen chunk; chunks never overlap.
   * A single highlight pill glides from word to word as they are spoken; spoken words stay bright.
   */
  captions() {
    const wrap = h('div', { class: 'cap' });
    this.layers.captions.append(wrap);
    const chunks = [];
    for (const s of this.timing.sentences) for (const ph of s.phrases) chunks.push({ s, ph });
    chunks.forEach(({ s, ph }, i) => {
      const next = chunks[i + 1];
      const sameSentence = next && next.s === s;
      const el = h('div', { class: 'cap-chunk' });
      const pill = h('i', { class: 'pill' });
      el.append(pill);
      const words = ph.words.map((w) => {
        const txt = h('b', {}, w.shown);
        const cw = h('span', { class: 'cw' }, txt);
        el.append(cw, ' ');
        return { w, cw, txt };
      });
      wrap.append(el);

      const t0 = ph.start - 0.06;
      // Linger a little after the last word, but always finish fading out before the next chunk starts to appear.
      const nextShow = next ? next.ph.start - 0.06 : Infinity;
      const hold = Math.max(ph.start + 0.2, Math.min(ph.end + (sameSentence ? 0.04 : 0.4), nextShow - 0.13));
      this.show(el, t0, { dur: 0.2, y: 16, ease: 'outCubic' });
      this.hide(el, hold, { dur: 0.12, y: -8, ease: 'inQuad' });

      // Geometry is measured once (fonts are loaded and the chunk is laid out, though not yet visible).
      const geo = words.map(({ cw }) => ({ x: cw.offsetLeft - 12, y: cw.offsetTop - 2, w: cw.offsetWidth + 24, h: cw.offsetHeight + 1 }));
      this.chan(pill, 'x', { initial: geo[0].x });
      this.chan(pill, 'y', { initial: geo[0].y });
      this.chan(pill, 'css:width', { initial: geo[0].w, unit: 'px' });
      this.chan(pill, 'css:height', { initial: geo[0].h, unit: 'px' });
      this.chan(pill, 'opacity').initial = 0;
      words.forEach(({ w, txt }, k) => {
        const g = geo[k];
        this.tween(pill, w.start - 0.04, 0.1, { x: g.x, y: g.y, 'css:width': g.w, 'css:height': g.h }, { ease: 'outCubic' });
        this.chan(txt, 'css:--r', { initial: 0 });
        this.tween(txt, w.start - 0.03, 0.1, { 'css:--r': 1 }, { ease: 'outCubic' });
      });
      this.tween(pill, ph.start - 0.05, 0.08, { opacity: 1 }, { ease: 'outCubic' });
      this.tween(pill, ph.end + 0.02, 0.16, { opacity: 0 }, { ease: 'outCubic' });
    });
    return wrap;
  }
}

// -------------------------------------------------------------------------------------------------
// Layout audit: finds out-of-bounds text, clipped text and overlapping text at chosen times.
// -------------------------------------------------------------------------------------------------

const effectiveOpacity = (el) => {
  let o = 1;
  for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
    const cs = getComputedStyle(n);
    if (cs.visibility === 'hidden' || cs.display === 'none') return 0;
    o *= parseFloat(cs.opacity);
  }
  return o;
};

export function audit(reel, times, { margin = 56, top = 150, bottom = 1700, width = 1080, fade = true } = {}) {
  const issues = [];
  for (const T of times) {
    reel.render(T);
    const boxes = [];
    const nodes = reel.layers.scenes.querySelectorAll('*');
    const caps = reel.layers.captions.querySelectorAll('.cap-chunk');
    for (const el of [...nodes, ...caps]) {
      const hasText = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
      const isNode = el.classList?.contains('gn'); // a map node: its whole pill is checked too, not just the text
      if (!hasText && !isNode && !(el instanceof SVGTextElement)) continue;
      if (el.closest('[data-audit-skip]')) continue;
      if (effectiveOpacity(el) < 0.6) continue;
      const r = el.getBoundingClientRect();
      if (r.width < 1 || r.height < 1) continue;
      const label = isNode ? `node.${el.className.split(' ')[1] ?? ''} "${el.textContent.trim().slice(0, 36)}"` : `${el.tagName.toLowerCase()}${el.className && typeof el.className === 'string' ? '.' + el.className.split(' ')[0] : ''} "${el.textContent.trim().slice(0, 36)}"`;
      const mg = isNode ? margin - 18 : margin;
      const vp = el.closest('[data-viewport]');
      if (vp) {
        if ((reel.quiet ?? []).some(([a, b]) => T > a - 0.05 && T < b + 0.05)) continue;
        // Inside a camera viewport: ignore what the camera is not looking at, flag text cut by the frame or sitting in the fade zones.
        const v = vp.getBoundingClientRect();
        const ix = Math.min(r.right, v.right) - Math.max(r.left, v.left), iy = Math.min(r.bottom, v.bottom) - Math.max(r.top, v.top);
        if (ix <= 0 || iy <= 0 || (ix * iy) / (r.width * r.height) < 0.5) continue;
        if (r.left < mg - 1 || r.right > width - mg + 1) issues.push({ t: T, kind: 'bounds', what: label, rect: [r.left, r.top, r.right, r.bottom].map(Math.round) });
        else if (fade && (r.top < v.top + 50 || r.bottom > v.bottom - 50)) issues.push({ t: T, kind: 'fade', what: label, rect: [r.left, r.top, r.right, r.bottom].map(Math.round) });
      } else if (!el.closest('[data-bleed]') && (r.left < mg - 1 || r.right > width - mg + 1 || r.top < top || r.bottom > bottom)) {
        issues.push({ t: T, kind: 'bounds', what: label, rect: [r.left, r.top, r.right, r.bottom].map(Math.round) });
      }
      if (el.scrollWidth > el.clientWidth + 2 && getComputedStyle(el).overflow !== 'visible') {
        issues.push({ t: T, kind: 'clipped', what: label });
      }
      boxes.push({ label, r, el });
    }
    for (let i = 0; i < boxes.length; i++) {
      for (let j = i + 1; j < boxes.length; j++) {
        const a = boxes[i], b = boxes[j];
        if (a.el.contains(b.el) || b.el.contains(a.el) || a.el.closest('[data-overlap-ok]') || b.el.closest('[data-overlap-ok]')) continue;
        const w = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left);
        const hh = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
        if (w > 4 && hh > 4) {
          const frac = (w * hh) / Math.min(a.r.width * a.r.height, b.r.width * b.r.height);
          if (frac > 0.12) issues.push({ t: T, kind: 'overlap', what: `${a.label} × ${b.label}`, frac: +frac.toFixed(2) });
        }
      }
    }
  }
  return issues;
}
