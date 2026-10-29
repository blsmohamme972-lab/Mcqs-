// Maps and flow charts. A World is a large canvas seen through a viewport with a camera: nodes and detail blocks are
// placed in world coordinates, edges are routed and drawn on, and the camera flies to whatever the narrator is
// talking about. Everything is scheduled at absolute times (usually `R.s.<sentence>.at('word')`), so the picture
// follows the voice-over word by word.
//
//   const W = new World(R, sc, { size: [1080, 3200] });
//   const a = W.node('a', { kind: 'step', icon: 'heart-pulse', label: 'Describe', sub: 'classic or atypical', tone: 'pink', x: 540, y: 300 });
//   const b = W.node('b', { kind: 'decision', label: 'On exertion?', x: 540, y: 600 });
//   W.edge(a, b, { label: 'then' });
//   W.start('a');                         // initial camera
//   a.in(1.2); W.go(1.1, 'a');            // appear + camera (lights the node, dims the previous one)
//   W.edge(a, b).in(4); b.in(4.4); W.go(4, 'b');

import { h } from './dom.js';
import { toneVar, drawPath } from './components.js';
import { layered } from './layout.js';
import { pointAt } from './geom.js';

export const VIEW = { x: 0, y: 180, w: 1080, h: 1220 };
const FADE = 76; // px of the viewport faded at the top and bottom (matches the CSS mask)
const f1 = (v) => Math.round(v * 10) / 10;

/** "text with *emphasis*" → text nodes and gradient italics. */
export const fmt = (text) => String(text).split(/(\*[^*]+\*)/).filter(Boolean).map((p) => (p.startsWith('*') ? h('em', { class: 'grad' }, p.slice(1, -1)) : p));

const NORMAL = { b: [0, 1], t: [0, -1], l: [-1, 0], r: [1, 0] };

/** Polyline with rounded corners as an SVG path. */
export function roundedPath(pts, radius = 26) {
  let d = `M${f1(pts[0][0])} ${f1(pts[0][1])}`;
  for (let i = 1; i < pts.length - 1; i++) {
    const A = pts[i - 1], V = pts[i], B = pts[i + 1];
    const la = Math.hypot(A[0] - V[0], A[1] - V[1]), lb = Math.hypot(B[0] - V[0], B[1] - V[1]);
    if (la < 1e-6 || lb < 1e-6) continue;
    const d1 = Math.min(radius, la / 2), d2 = Math.min(radius, lb / 2);
    d += ` L${f1(V[0] + ((A[0] - V[0]) / la) * d1)} ${f1(V[1] + ((A[1] - V[1]) / la) * d1)} Q${f1(V[0])} ${f1(V[1])} ${f1(V[0] + ((B[0] - V[0]) / lb) * d2)} ${f1(V[1] + ((B[1] - V[1]) / lb) * d2)}`;
  }
  const L = pts.at(-1);
  return `${d} L${f1(L[0])} ${f1(L[1])}`;
}

class WNode {
  constructor(W, id, el, spec) {
    Object.assign(this, { W, R: W.R, id, el, spec });
    W.el.append(el);
    this.w = el.offsetWidth;
    this.h = el.offsetHeight;
    this.R.chan(el, 'css:--lit', { initial: spec.lit ?? 0 });
    this.tone = spec.tone ?? 'neutral';
    if (spec.x != null) this.place(spec.x, spec.y);
  }

  place(x, y) {
    this.x = x; this.y = y;
    this.el.style.left = `${f1(x - this.w / 2)}px`;
    this.el.style.top = `${f1(y - this.h / 2)}px`;
    return this;
  }

  get box() { return { x: this.x - this.w / 2, y: this.y - this.h / 2, w: this.w, h: this.h }; }

  /** Port on a side ('t' 'b' 'l' 'r') with an offset (px) along that side. */
  port(side, off = 0) {
    const { x, y, w, h } = this;
    return { t: [x + off, y - h / 2], b: [x + off, y + h / 2], l: [x - w / 2, y + off], r: [x + w / 2, y + off] }[side];
  }

  in(t, o = {}) {
    this.shownAt = Math.min(this.shownAt ?? Infinity, t);
    this.R.show(this.el, t, { dur: 0.6, y: 26, scale: 0.97, ease: 'outExpo', ...o });
    return this;
  }
  out(t, o = {}) { this.R.hide(this.el, t, { dur: 0.3, y: 0, ...o }); return this; }
  lit(t, v = 1, dur = 0.4) { this.R.tween(this.el, t, dur, { 'css:--lit': v }, { ease: 'outCubic' }); return this; }
  pop(t, amt = 0.045) {
    this.R.tween(this.el, t, 0.16, { scale: 1 + amt }, { ease: 'outCubic' });
    this.R.tween(this.el, t + 0.16, 0.45, { scale: 1 }, { ease: 'outSoft' });
    return this;
  }
}

class WEdge {
  constructor(W, a, b, spec = {}) {
    const R = W.R;
    Object.assign(this, { W, R, a, b, spec });
    const tone = spec.tone ?? b.tone ?? 'neutral';
    const from = [].concat(spec.from ?? 'b'), to = [].concat(spec.to ?? 't');
    const p0 = a.port(from[0], from[1] ?? 0), p1 = b.port(to[0], to[1] ?? 0);
    const kind = spec.route ?? 'elbow';
    let d, tail; // tail: direction of arrival at p1
    const pts = [p0];
    if (kind === 'curve') {
      const n0 = NORMAL[from[0]], n1 = NORMAL[to[0]];
      const k = Math.max(70, Math.hypot(p1[0] - p0[0], p1[1] - p0[1]) * 0.42);
      const c1 = [p0[0] + n0[0] * k, p0[1] + n0[1] * k], c2 = [p1[0] + n1[0] * k, p1[1] + n1[1] * k];
      d = `M${f1(p0[0])} ${f1(p0[1])} C${f1(c1[0])} ${f1(c1[1])} ${f1(c2[0])} ${f1(c2[1])} ${f1(p1[0])} ${f1(p1[1])}`;
      tail = [p1[0] - c2[0], p1[1] - c2[1]];
      // sample for label placement
      for (let i = 1; i <= 24; i++) {
        const u = i / 24, v = 1 - u;
        pts.push([v ** 3 * p0[0] + 3 * v * v * u * c1[0] + 3 * v * u * u * c2[0] + u ** 3 * p1[0], v ** 3 * p0[1] + 3 * v * v * u * c1[1] + 3 * v * u * u * c2[1] + u ** 3 * p1[1]]);
      }
    } else {
      if (spec.via) pts.push(...spec.via);
      else if (kind === 'elbow') {
        const vert0 = from[0] === 'b' || from[0] === 't', vert1 = to[0] === 'b' || to[0] === 't';
        if (vert0 && vert1 && Math.abs(p0[0] - p1[0]) > 0.5) { const my = spec.bend ?? (p0[1] + p1[1]) / 2; pts.push([p0[0], my], [p1[0], my]); }
        else if (!vert0 && !vert1 && Math.abs(p0[1] - p1[1]) > 0.5) { const mx = spec.bend ?? (p0[0] + p1[0]) / 2; pts.push([mx, p0[1]], [mx, p1[1]]); }
        else if (vert0 && !vert1) pts.push([p0[0], p1[1]]);
        else if (!vert0 && vert1) pts.push([p1[0], p0[1]]);
      }
      pts.push(p1);
      d = kind === 'line' ? `M${pts.map((p) => `${f1(p[0])} ${f1(p[1])}`).join(' L')}` : roundedPath(pts, spec.radius ?? 26);
      const q = pts.at(-2);
      tail = [p1[0] - q[0], p1[1] - q[1]];
    }
    this.pts = pts;
    this.tone = tone;
    const style = { '--tone': toneVar(tone), '--lit': 1 };
    this.path = h('path', { class: 'ed', d, style: { ...style, ...(spec.dashed ? { strokeDasharray: '2 14' } : {}) } });
    W.svg.append(this.path);
    R.chan(this.path, 'css:--lit', { initial: spec.lit ?? 1 });

    if (spec.arrow !== false) {
      const L = Math.hypot(tail[0], tail[1]) || 1, ux = tail[0] / L, uy = tail[1] / L, s = spec.arrowSize ?? 15;
      const tip = [p1[0] + ux * 2, p1[1] + uy * 2];
      const bx = tip[0] - ux * s * 1.15, by = tip[1] - uy * s * 1.15;
      this.head = h('path', { class: 'ed-head', d: `M${f1(tip[0])} ${f1(tip[1])} L${f1(bx - uy * s * 0.62)} ${f1(by + ux * s * 0.62)} L${f1(bx + uy * s * 0.62)} ${f1(by - ux * s * 0.62)} Z`, style: { '--tone': toneVar(tone) } });
      W.svg.append(this.head);
      R.chan(this.head, 'opacity').initial = 0;
      R.chan(this.head, 'css:--lit', { initial: spec.lit ?? 1 });
    }
    if (spec.dot !== false) {
      this.dot = h('circle', { class: 'ed-dot', r: spec.dotSize ?? 8, style: { '--tone': toneVar(tone) } });
      W.svg.append(this.dot);
      R.chan(this.dot, 'opacity').initial = 0;
    }
    if (spec.label != null) {
      const at = pointAt(pts, spec.labelAt ?? 0.5);
      this.label = h('div', { class: 'el', style: { '--tone': toneVar(tone) } }, spec.label);
      W.el.append(this.label);
      this.label.style.left = `${f1(at[0] - this.label.offsetWidth / 2)}px`;
      this.label.style.top = `${f1(at[1] - this.label.offsetHeight / 2)}px`;
    }
  }

  length() { return (this._len ??= this.path.getTotalLength()); }

  /** Draw the connector on between t and t+dur, with a travelling pulse and a popping arrowhead. */
  in(t, dur = 0.6) {
    const R = this.R;
    this.shownAt = Math.min(this.shownAt ?? Infinity, t);
    drawPath(R, this.path, t, dur, { ease: 'inOutCubic' });
    if (this.head) R.show(this.head, t + dur * 0.82, { dur: 0.3, y: 0, scale: 0.4, ease: 'outCubic' });
    if (this.label) R.show(this.label, t + dur * 0.35, { dur: 0.45, y: 8, ease: 'outCubic' });
    if (this.dot) {
      R.tween(this.dot, t, 0.1, { opacity: 1 });
      R.tween(this.dot, t + dur, 0.25, { opacity: 0 });
      R.fn(t, t + dur, (p) => { const q = this.path.getPointAtLength(p * this.length()); this.dot.setAttribute('cx', q.x); this.dot.setAttribute('cy', q.y); }, { ease: 'inOutCubic' });
    }
    return this;
  }

  lit(t, v = 1, dur = 0.4) {
    for (const el of [this.path, this.head]) if (el) this.R.tween(el, t, dur, { 'css:--lit': v }, { ease: 'outCubic' });
    return this;
  }

  out(t, dur = 0.45) {
    for (const el of [this.path, this.head, this.label]) if (el) this.R.hide(el, t, { dur, y: 0 });
    return this;
  }
}

export class World {
  constructor(R, sc, { view = VIEW, size = [1080, 3600], anchor = [540, 340], grid = true } = {}) {
    Object.assign(this, { R, view, size, anchor });
    (globalThis.__worlds ??= []).push(this); // handy for debugging in the page
    this.nodes = {};
    this.edges = [];
    this.zones = [];
    this._active = null;
    this.vp = h('div', { class: 'viewport', 'data-viewport': '', style: { left: `${view.x}px`, top: `${view.y}px`, width: `${view.w}px`, height: `${view.h}px` } });
    this.bg = grid ? h('div', { class: 'vp-bg' }) : null;
    this.el = h('div', { class: 'world', style: { width: `${size[0]}px`, height: `${size[1]}px` } });
    this.svg = h('svg', { class: 'edges', width: size[0], height: size[1], viewBox: `0 0 ${size[0]} ${size[1]}` });
    this.el.append(this.svg);
    this.vp.append(...(this.bg ? [this.bg] : []), this.el);
    sc.add(this.vp);
    for (const [k, v] of Object.entries({ x: 0, y: 0, scale: 1 })) R.chan(this.el, k, { initial: v });
    if (this.bg) {
      const cx = R.chan(this.el, 'x'), cy = R.chan(this.el, 'y'), cs = R.chan(this.el, 'scale');
      R.fn(0, R.duration, (_p, T) => {
        const s = cs.at(T);
        this.bg.style.backgroundPosition = `${f1(cx.at(T) * 0.55)}px ${f1(cy.at(T) * 0.55)}px`;
        this.bg.style.backgroundSize = `${f1(64 * (0.7 + 0.3 * s))}px ${f1(64 * (0.7 + 0.3 * s))}px`;
      });
    }
  }

  // ------------------------------------------------------------------ nodes
  /** kinds: step · chip · tag · decision · start · end · note · title. */
  node(id, spec = {}) {
    const R = this.R, kind = spec.kind ?? 'step';
    const tone = spec.tone ?? 'neutral';
    const ic = spec.icon ? R.icon(spec.icon, { size: spec.iconSize ?? ({ step: 52, start: 66, chip: 42, decision: 48, end: 46, tag: 34 }[kind] ?? 40), stroke: 1.8 }) : null;
    const text = h('div', { class: 'tx' }, h('div', { class: 'lb' }, ...fmt(spec.label ?? '')), spec.sub ? h('div', { class: 'sb' }, ...fmt(spec.sub)) : null);
    let kids;
    if (kind === 'step' || kind === 'start') kids = [ic ? h('div', { class: 'ic' }, ic) : null, text];
    else if (kind === 'chip' || kind === 'end' || kind === 'decision' || kind === 'tag') kids = [ic, text];
    else kids = [text];
    if (spec.num != null) kids.push(h('b', { class: 'num' }, spec.num));
    const el = h('div', { class: ['gn', kind, spec.cls], style: { '--tone': toneVar(tone), ...(spec.w ? { width: `${spec.w}px` } : {}), ...(spec.style ?? {}) } }, ...kids);
    const n = new WNode(this, id, el, spec);
    this.nodes[id] = n;
    return n;
  }

  n(id) { const n = typeof id === 'string' ? this.nodes[id] : id; if (!n) throw new Error(`unknown node ${id}`); return n; }

  /** Lay the given nodes out top-down with the layered algorithm and place them (centres). */
  layout(ids, edges, opts = {}) {
    const nodes = ids.map((id) => { const n = this.n(id); return { id, w: n.w, h: n.h, rank: this.nodes[id].spec.rank }; });
    const pos = layered(nodes, edges, { x0: this.size[0] / 2, gapY: 110, ...opts });
    for (const [id, p] of Object.entries(pos)) this.nodes[id].place(p.x, p.y);
    return pos;
  }

  edge(a, b, spec) {
    const e = new WEdge(this, this.n(a), this.n(b), spec);
    this.edges.push(e);
    return e;
  }

  /**
   * Items stacked under a parent and left-aligned, joined to it by a bracket (vertical trunk + a short branch per item).
   * Returns { nodes, edges }; nothing is revealed yet, so cue each node and edge yourself.
   */
  outline(parent, items, { x, y, gap = 20, trunk = 36, tone, kind = 'chip', arrowSize = 11 } = {}) {
    const p = this.n(parent);
    const left = x ?? p.box.x + trunk + 26;
    let top = y ?? p.box.y + p.h + 34;
    const nodes = [], edges = [];
    for (const it of items) {
      const n = this.node(it.id, { kind, tone, ...it });
      n.place(left + n.w / 2, top + n.h / 2);
      top += n.h + gap;
      edges.push(this.edge(p, n, { from: ['b', left - trunk - p.x], to: 'l', tone: it.tone ?? tone, arrowSize }));
      nodes.push(n);
    }
    return { nodes, edges, bottom: top - gap };
  }

  /** Small nodes in a left-aligned grid (column widths follow the widest item). */
  grid(items, { x, y, cols = 2, gapX = 16, gapY = 16, kind = 'tag', tone } = {}) {
    const nodes = items.map((it) => this.node(it.id, { kind, tone, ...it }));
    const colW = Array.from({ length: cols }, (_, c) => Math.max(...nodes.filter((_, i) => i % cols === c).map((n) => n.w)));
    const rowH = Array.from({ length: Math.ceil(nodes.length / cols) }, (_, r) => Math.max(...nodes.slice(r * cols, r * cols + cols).map((n) => n.h)));
    nodes.forEach((n, i) => {
      const c = i % cols, r = Math.floor(i / cols);
      const nx = x + colW.slice(0, c).reduce((a, b) => a + b + gapX, 0), ny = y + rowH.slice(0, r).reduce((a, b) => a + b + gapY, 0);
      n.place(nx + n.w / 2, ny + rowH[r] / 2);
    });
    return nodes;
  }

  /** Any element (or element list) placed in the world; `at` is the centre (anchor 'c'), top-left ('tl') or top-centre ('tc'). */
  put(el, { x, y, anchor = 'c' } = {}) {
    this.el.append(el);
    el.style.position = 'absolute';
    const w = el.offsetWidth, hh = el.offsetHeight;
    const ox = anchor === 'tl' ? 0 : w / 2, oy = anchor === 'c' ? hh / 2 : 0;
    el.style.left = `${f1(x - ox)}px`;
    el.style.top = `${f1(y - oy)}px`;
    return el;
  }

  /** A soft region (swim lane / zone) behind nodes. */
  lane({ x, y, w, h: hh, tone = 'neutral', label, dashed = true }) {
    const el = h('div', { class: ['lane', dashed && 'dashed'], style: { left: `${x}px`, top: `${y}px`, width: `${w}px`, height: `${hh}px`, '--tone': toneVar(tone) } }, label ? h('div', { class: 'lane-lb' }, label) : null);
    this.el.insertBefore(el, this.svg); // lanes sit below the edge layer
    return el;
  }

  /** A district: a soft region around a group of nodes, with a small label. Returns { el, rect, in(t) }. */
  zone(ids, { tone = 'neutral', label, pad = 64, dashed = true, extra = [] } = {}) {
    const bs = [...ids.map((id) => this.n(id).box), ...extra];
    const x0 = Math.min(...bs.map((b) => b.x)) - pad, y0 = Math.min(...bs.map((b) => b.y)) - pad;
    const x1 = Math.max(...bs.map((b) => b.x + b.w)) + pad, y1 = Math.max(...bs.map((b) => b.y + b.h)) + pad + (label ? 46 : 0);
    const el = this.lane({ x: x0, y: y0, w: x1 - x0, h: y1 - y0, tone, label, dashed });
    const R = this.R;
    R.chan(el, 'opacity').initial = 0;
    const W = this;
    const z = {
      el, ids, pad, label, extra, rect: { x: x0, y: y0, w: x1 - x0, h: y1 - y0 },
      in(t) { this.shownAt = Math.min(this.shownAt ?? Infinity, t); R.show(el, t, { dur: 0.9, y: 0, scale: 0.985, ease: 'outCubic' }); return this; },
      out(t) { R.hide(el, t, { dur: 0.5, y: 0 }); return this; },
      /**
       * The district starts around its first revealed item and grows to hold each node (and each timed extra rect:
       * `extra: [{ x, y, w, h, t }]`) as it is revealed. Extras without `t` are part of the district from the start.
       */
      grow() {
        const items = [
          ...ids.map((id) => W.n(id)).filter((n) => n.shownAt != null).map((n) => ({ t: n.shownAt, r: n.box })),
          ...this.extra.map((e) => ({ t: e.t ?? -Infinity, r: e })),
        ].sort((a, b) => a.t - b.t);
        const first = items.findIndex((it) => it.t > -Infinity);
        if (first < 0) return this;
        const labelPad = label ? 46 : 0;
        const rectAt = (k) => {
          const bs = items.slice(0, k + 1).map((it) => it.r);
          const rx0 = Math.min(...bs.map((b) => b.x)) - pad, ry0 = Math.min(...bs.map((b) => b.y)) - pad;
          return { 'css:left': rx0, 'css:top': ry0, 'css:width': Math.max(...bs.map((b) => b.x + b.w)) + pad - rx0, 'css:height': Math.max(...bs.map((b) => b.y + b.h)) + pad + labelPad - ry0 };
        };
        for (const [k, v] of Object.entries(rectAt(first))) R.chan(el, k, { initial: v, unit: 'px' });
        for (let k = first + 1; k < items.length; k++) R.tween(el, items[k].t - 0.3, 0.75, rectAt(k), { ease: 'outCubic' });
        return this;
      },
    };
    this.zones.push(z);
    return z;
  }

  /** Call once at the end of a reel's build: lets every zone grow with its content. */
  finish() { this.zones.forEach((z) => z.grow()); return this; }

  // ------------------------------------------------------------------ camera
  _resolve(target, { zoom, anchor, fit, pad = 70, max = 1.15 } = {}) {
    let rect = null, pt = null;
    if (typeof target === 'string' || target instanceof WNode) { const n = this.n(target); pt = [n.x, n.y]; rect = n.box; }
    else if (Array.isArray(target) && typeof target[0] === 'string') {
      const bs = target.map((id) => this.n(id).box);
      const x0 = Math.min(...bs.map((b) => b.x)), y0 = Math.min(...bs.map((b) => b.y));
      rect = { x: x0, y: y0, w: Math.max(...bs.map((b) => b.x + b.w)) - x0, h: Math.max(...bs.map((b) => b.y + b.h)) - y0 };
      fit = true;
    } else if (Array.isArray(target)) pt = target;
    else if (target && 'w' in target) { rect = target; fit = true; }
    if (fit && rect) {
      const z = zoom ?? Math.min((this.view.w - 2 * pad) / rect.w, (this.view.h - 2 * FADE - pad) / rect.h, max);
      return { px: rect.x + rect.w / 2, py: rect.y + rect.h / 2, z, a: anchor ?? [this.view.w / 2, this.view.h / 2] };
    }
    return { px: pt[0], py: pt[1], z: zoom ?? 1, a: anchor ?? this.anchor };
  }

  /** Camera pose at time 0. */
  start(target, o = {}) {
    const { px, py, z, a } = this._resolve(target, o);
    const R = this.R;
    R.chan(this.el, 'x').initial = a[0] - z * px;
    R.chan(this.el, 'y').initial = a[1] - z * py;
    R.chan(this.el, 'scale').initial = z;
    return this;
  }

  /** Fly the camera to a node, a list of nodes (fit), a point [x, y] or a rect {x,y,w,h} (fit). */
  cam(t, target, { dur = 1.0, ease = 'inOutCubic', ...o } = {}) {
    const { px, py, z, a } = this._resolve(target, o);
    this.R.tween(this.el, t, dur, { x: a[0] - z * px, y: a[1] - z * py, scale: z }, { ease });
    (this.R.quiet ??= []).push([t, t + dur]); // the audit ignores frames while the camera is moving
    return this;
  }

  /**
   * Camera + highlight: flies to a node (or fits a list of nodes), lights the node and dims the previously active one.
   * Everything already shown that the new view would still catch (and that is not part of the focus) fades away, so
   * the frame never shows stray fragments of the previous cluster. Pass `cull: false` to keep them.
   */
  go(t, id, { dur = 1.0, dim = 0.38, lit = 1, fit, cull = true, ...o } = {}) {
    const n = this.n(id);
    const target = fit?.rect ?? fit ?? n;
    this.cam(t, target, { dur, ...o });
    if (cull) this._cull(t + 0.08, this._resolve(target, o), this._keepSet(n, fit));
    if (this._active && this._active !== n) this._active.lit(t, dim, 0.5);
    n.lit(t + dur * 0.35, lit, 0.45);
    this._active = n;
    return this;
  }

  /** Nodes (and zones) that belong to a focus: the head node, listed ids, or everything inside a rect/zone. */
  _keepSet(head, fit) {
    const keep = new Set([head]);
    if (Array.isArray(fit)) fit.forEach((k) => keep.add(this.n(k)));
    else if (fit) {
      const r = fit.rect ?? fit;
      for (const n of Object.values(this.nodes)) if (n.x > r.x && n.x < r.x + r.w && n.y > r.y && n.y < r.y + r.h) keep.add(n);
      for (const z of this.zones) if (z === fit || (z.rect.x >= r.x - 4 && z.rect.y >= r.y - 4 && z.rect.x + z.rect.w <= r.x + r.w + 4 && z.rect.y + z.rect.h <= r.y + r.h + 4)) keep.add(z);
    }
    if (fit?.rect) keep.add(fit);
    return keep;
  }

  _cull(t, { px, py, z, a }, keep) {
    // bring back anything this focus needs that an earlier camera move faded out
    for (const n of keep) if (n.culled) { n.culled = false; n.in(t + 0.4, { dur: 0.5 }); }
    for (const e of this.edges) if (e.culled && (keep.has(e.a) || keep.has(e.b))) { e.culled = false; e.in(t + 0.4, 0.01); for (const el of [e.path, e.head, e.label]) if (el) this.R.tween(el, t + 0.4, 0.4, { opacity: 1 }); }
    // leaving a cluster fades it, even if the new view would not catch it: the camera flight stays clean
    for (const k of this._prevKeep ?? []) {
      if (keep.has(k) || k.culled || k.shownAt == null || k.shownAt > t || k.spec?.keep) continue;
      k.out(t, { dur: 0.45 });
      k.culled = true;
    }
    this._prevKeep = keep;
    const tx = a[0] - z * px, ty = a[1] - z * py, m = 30;
    const x0 = -tx / z - m, x1 = (this.view.w - tx) / z + m, y0 = -ty / z - m, y1 = (this.view.h - ty) / z + m;
    for (const n of Object.values(this.nodes)) {
      if (n.shownAt == null || n.shownAt > t || n.culled || keep.has(n) || n.spec.keep) continue;
      const b = n.box;
      if (b.x < x1 && b.x + b.w > x0 && b.y < y1 && b.y + b.h > y0) { n.out(t, { dur: 0.45 }); n.culled = true; }
    }
    for (const zn of this.zones) {
      if (zn.culled && keep.has(zn)) { zn.culled = false; zn.in(t + 0.4); continue; }
      if (zn.shownAt == null || zn.shownAt > t || zn.culled || keep.has(zn)) continue;
      const r = zn.rect;
      if (r.x < x1 && r.x + r.w > x0 && r.y < y1 && r.y + r.h > y0) { zn.out(t); zn.culled = true; }
    }
    for (const e of this.edges) {
      if (e.shownAt == null || e.shownAt > t || e.culled || keep.has(e.a) || keep.has(e.b)) continue;
      if (e.a.culled || e.b.culled) { e.out(t); e.culled = true; }
    }
  }

  /** Reveal a node (and the edge leading to it) at t, flash it, then settle it to a dim state after `hold` seconds. */
  appear(n, edge, t, { hold = 1.3, settle = 0.32 } = {}) {
    const node = this.n(n);
    if (edge) edge.in(t);
    node.in(t + (edge ? 0.32 : 0));
    node.lit(t + 0.3, 1, 0.3).pop(t + 0.35);
    if (hold < 90) node.lit(t + 0.3 + hold, settle, 0.7);
    return this;
  }
}

/** Compact icon + label pill (also used for the leaves of trees). */
export function chip(R, { icon, label, tone = 'neutral', size = 38, cls = '' }) {
  return h('div', { class: ['gn', 'chip', cls, 'inflow'], style: { '--tone': toneVar(tone), fontSize: `${size}px` } }, icon ? R.icon(icon, { size: size * 1.05, stroke: 1.8 }) : null, h('div', { class: 'tx' }, h('div', { class: 'lb' }, ...fmt(label))));
}
