// Hologram hand (palmar or dorsal view) built from capsules, with named landmarks for clinical signs.
// The silhouette is the union of the finger / thumb / palm / forearm shapes: every shape is stroked first and then filled
// on top, so only the outer contour keeps its line. Coordinates: viewBox 400 × 640, fingers up, forearm at the bottom.

import { h } from './dom.js';

export const HAND_W = 400, HAND_H = 640;

const FINGERS = [
  { name: 'index', bx: 138, by: 296, w: 50, len: 196, rot: -7 },
  { name: 'middle', bx: 190, by: 280, w: 52, len: 222, rot: -1.5 },
  { name: 'ring', bx: 244, by: 288, w: 50, len: 204, rot: 4 },
  { name: 'little', bx: 292, by: 318, w: 44, len: 158, rot: 11 },
];

/** Rotate point (x, y) around (cx, cy) by deg. */
const rot = ([x, y], [cx, cy], deg) => {
  const a = (deg * Math.PI) / 180, c = Math.cos(a), s = Math.sin(a);
  return [cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c];
};

/**
 * hand(R, { x, y, scale, view: 'palmar' | 'dorsal', id }) → { svg, pt([hx, hy]) → world px, LM, shapes }
 * LM (hand coordinates): tips[], pulps[], nails[], knuckles[], palm, thenar, hypothenar, wrist, forearm, tendons[].
 */
export function hand(R, { x, y, scale = 0.8, view = 'palmar', id = 'h', mirror = false } = {}) {
  const flip = (pt) => (mirror ? [HAND_W - pt[0], pt[1]] : pt);
  const caps = [];
  // palm and forearm
  caps.push(h('rect', { x: 92, y: 288, width: 216, height: 250, rx: 74 }));
  caps.push(h('rect', { x: 132, y: 500, width: 136, height: 150, rx: 34 }));
  // fingers
  FINGERS.forEach((f) => caps.push(h('rect', { x: f.bx - f.w / 2, y: f.by - f.len, width: f.w, height: f.len + 40, rx: f.w / 2, transform: `rotate(${f.rot} ${f.bx} ${f.by})` })));
  // thumb
  const th = { bx: 112, by: 430, w: 58, len: 170, rot: -52 };
  caps.push(h('rect', { x: th.bx - th.w / 2, y: th.by - th.len, width: th.w, height: th.len + 40, rx: th.w / 2, transform: `rotate(${th.rot} ${th.bx} ${th.by})` }));

  const clipId = `${id}clip`;
  const svg = h('svg', { class: 'hand', viewBox: `0 0 ${HAND_W} ${HAND_H}`, width: HAND_W * scale, height: HAND_H * scale, style: { position: 'absolute', left: `${x}px`, top: `${y}px`, overflow: 'visible' } },
    h('defs', {},
      h('linearGradient', { id: `${id}fill`, x1: 0, y1: 0, x2: 0, y2: 1 }, h('stop', { offset: '0', 'stop-color': '#2a2a3d' }), h('stop', { offset: '1', 'stop-color': '#191927' })),
      h('pattern', { id: `${id}scan`, width: 8, height: 12, patternUnits: 'userSpaceOnUse' }, h('rect', { width: 8, height: 1.4, fill: '#ffffff', 'fill-opacity': 0.07 })),
      h('clipPath', { id: clipId }, ...caps.map((c) => c.cloneNode(true)))),
    h('g', { class: 'hand-shapes', transform: mirror ? `translate(${HAND_W} 0) scale(-1 1)` : null },
      h('g', { stroke: '#cfd4ff', 'stroke-opacity': 0.75, 'stroke-width': 7, 'stroke-linejoin': 'round', fill: 'none' }, ...caps.map((c) => c.cloneNode(true))),
      h('g', { fill: `url(#${id}fill)`, stroke: 'none' }, ...caps.map((c) => c.cloneNode(true))),
      h('rect', { x: 0, y: 0, width: HAND_W, height: HAND_H, fill: `url(#${id}scan)`, 'clip-path': `url(#${clipId})` })));

  const tipOf = (f) => rot([f.bx, f.by - f.len + 26], [f.bx, f.by], f.rot);
  const tips = FINGERS.map(tipOf);
  const nails = FINGERS.map((f) => rot([f.bx, f.by - f.len + 36], [f.bx, f.by], f.rot));
  const thTip = rot([th.bx, th.by - th.len + 26], [th.bx, th.by], th.rot);
  const LM = {
    tips: [...tips, thTip].map(flip),                                 // index, middle, ring, little, thumb
    pulps: [...tips, thTip].map(flip),
    nails: [...nails, rot([th.bx, th.by - th.len + 36], [th.bx, th.by], th.rot)].map(flip),
    knuckles: FINGERS.map((f) => flip([f.bx, f.by + 8])),
    palm: flip([200, 390]), thenar: flip([138, 420]), hypothenar: flip([268, 430]), wrist: flip([200, 520]), forearm: flip([200, 590]),
    tendons: FINGERS.map((f) => [flip([f.bx, f.by - 20]), flip([f.bx, f.by + 70])]),
  };
  const pt = ([hx, hy]) => [x + hx * scale, y + hy * scale];
  return { svg, pt, scale, LM, view, w: HAND_W * scale, h: HAND_H * scale, FINGERS };
}
