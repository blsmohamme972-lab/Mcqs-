// Hologram-style front-view body for pain maps and examination points.
// Drawn from smooth point outlines; landmarks are in body coordinates (viewBox 560 × 1080).

import { h } from './dom.js';
import { smooth, mirrorHalf } from './geom.js';
import { toneVar, drawPath } from './components.js';

export const BODY_W = 560, BODY_H = 1080, CX = 280;

/** Anatomical landmarks (body coordinates). "left"/"right" are the patient's, so the left side is on the viewer's right. */
export const LM = {
  head: [CX, 108], jaw: [CX + 34, 168], neck: [CX, 214], carotid: [CX + 22, 222],
  chest: [CX, 392], heart: [CX + 30, 410], leftChest: [CX + 70, 400], leftShoulder: [CX + 150, 290],
  epigastrium: [CX, 540], abdomen: [CX, 640], groin: [CX + 62, 792],
  leftArm: [CX + 198, 470], leftWrist: [CX + 236, 702], rightWrist: [CX - 236, 702],
  leftHand: [CX + 250, 790], rightHand: [CX - 250, 790],
  leftKnee: [CX + 94, 905], leftCalf: [CX + 88, 965], leftAnkle: [CX + 86, 1036], leftFoot: [CX + 84, 1060],
  rightKnee: [CX - 94, 905], rightCalf: [CX - 88, 965], rightAnkle: [CX - 86, 1036], rightFoot: [CX - 84, 1060],
};

// Right half of the body (viewer's right) as [dx from axis, y]; legs run down to the feet and back up to the crotch.
const bodyHalf = [
  [30, 170], [30, 232], [90, 252], [142, 270], [172, 294], [168, 346], [154, 432], [140, 522], [132, 584], [146, 656], [158, 740],
  [152, 810], [144, 890], [130, 970], [118, 1040], [112, 1066], [64, 1068], [58, 1040], [52, 970], [44, 900], [30, 838], [0, 814],
];
const armHalf = [[166, 288], [204, 324], [226, 420], [238, 520], [246, 610], [262, 712], [272, 800], [246, 814], [224, 764], [206, 682], [194, 600], [182, 520], [172, 432], [166, 352]];
const headPts = [[CX - 54, 62], [CX, 34], [CX + 54, 62], [CX + 61, 112], [CX + 44, 162], [CX, 192], [CX - 44, 162], [CX - 61, 112]];

/** Returns the SVG element and helpers. `scale` maps body units to px; (x, y) is the top-left in px. */
export function body(R, { x, y, scale = 0.9, id = 'b' } = {}) {
  const w = BODY_W * scale, hgt = BODY_H * scale;
  const torso = smooth(mirrorHalf(bodyHalf, CX), { closed: true });
  const arm1 = smooth(armHalf.map(([dx, ay]) => [CX + dx, ay]), { closed: true });
  const arm2 = smooth(armHalf.map(([dx, ay]) => [CX - dx, ay]), { closed: true });
  const headPath = smooth(headPts, { closed: true });
  const svg = h('svg', { class: 'body', viewBox: `0 0 ${BODY_W} ${BODY_H}`, width: w, height: hgt, style: { position: 'absolute', left: `${x}px`, top: `${y}px`, overflow: 'visible' } },
    h('defs', {},
      h('linearGradient', { id: `${id}fill`, x1: 0, y1: 0, x2: 0, y2: 1 }, h('stop', { offset: '0', 'stop-color': '#ffffff', 'stop-opacity': 0.11 }), h('stop', { offset: '1', 'stop-color': '#ffffff', 'stop-opacity': 0.02 })),
      h('linearGradient', { id: `${id}edge`, x1: 0, y1: 0, x2: 0, y2: 1 }, h('stop', { offset: '0', 'stop-color': '#dfe3ff', 'stop-opacity': 0.8 }), h('stop', { offset: '1', 'stop-color': '#9aa0c8', 'stop-opacity': 0.28 })),
      h('pattern', { id: `${id}scan`, width: 8, height: 12, patternUnits: 'userSpaceOnUse' }, h('rect', { width: 8, height: 1.4, fill: '#ffffff', 'fill-opacity': 0.07 })),
      h('clipPath', { id: `${id}clip` }, h('path', { d: torso }), h('path', { d: arm1 }), h('path', { d: arm2 }), h('path', { d: headPath }))),
    h('g', { class: 'body-shapes' },
      ...[torso, arm1, arm2, headPath].map((d) => h('path', { d, fill: `url(#${id}fill)`, stroke: `url(#${id}edge)`, 'stroke-width': 3, 'stroke-linejoin': 'round' })),
      h('rect', { x: 0, y: 0, width: BODY_W, height: BODY_H, fill: `url(#${id}scan)`, 'clip-path': `url(#${id}clip)` })));
  /** Body point → absolute stage px. */
  const pt = ([bx, by]) => [x + bx * scale, y + by * scale];
  return { svg, pt, scale, w, h: hgt, LM };
}

// ---------------------------------------------------------------------------------------------
// Overlays: pulsing hotspots, leader-line callouts and flowing "radiation" paths
// ---------------------------------------------------------------------------------------------
/** Full-frame SVG used for leader lines and flow paths. */
export function overlay() {
  return h('svg', { class: 'ov', viewBox: '0 0 1080 1920', width: 1080, height: 1920, style: { position: 'absolute', left: 0, top: 0, overflow: 'visible', pointerEvents: 'none' } });
}

/**
 * Pulsing hotspot at stage px `at`. It appears at t0 and pulses until t1 (default: forever);
 * `strength` scales the ring size.
 */
export function hotspot(R, host, at, { tone = 'pink', t0, t1 = R.duration, size = 30, core = 11, beat = 0.9 } = {}) {
  const el = h('div', { class: 'hot', style: { left: `${at[0] - size}px`, top: `${at[1] - size}px`, width: `${size * 2}px`, height: `${size * 2}px`, '--tone': toneVar(tone), '--core': `${core}px` } },
    h('i', { class: 'r r2' }), h('i', { class: 'r r1' }), h('i', { class: 'core' }));
  host.append(el);
  R.show(el, t0, { dur: 0.5, scale: 0.4, y: 0, ease: 'outSoft' });
  const [r1, r2] = [el.querySelector('.r1'), el.querySelector('.r2')];
  R.fn(t0, t1, (_p, s) => {
    for (const [r, off] of [[r1, 0], [r2, 0.5]]) {
      const ph = ((s / beat) + off) % 1;
      r.style.transform = `scale(${0.35 + ph * 0.85})`;
      r.style.opacity = (1 - ph) * 0.9;
    }
  });
  return el;
}

/**
 * Callout: leader line from `from` to a label placed on `side` at height `ly`.
 * Returns { label, path, show(t), hide(t) }.
 */
export function callout(R, host, ov, { from, text, side = 'right', ly = from[1], lx, tone = 'teal', icon, size = 40 }) {
  const x = lx ?? (side === 'right' ? 812 : 268);
  const elbow = [side === 'right' ? from[0] + Math.max(36, (x - from[0]) * 0.35) : from[0] - Math.max(36, (from[0] - x) * 0.35), ly];
  const end = [x + (side === 'right' ? -14 : 14), ly];
  const path = h('path', { d: `M${from[0]} ${from[1]} L${elbow[0]} ${elbow[1]} L${end[0]} ${end[1]}`, fill: 'none', stroke: toneVar(tone), 'stroke-width': 3, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', opacity: 0.9 });
  ov.append(path);
  const label = h('div', { class: ['co', side], style: { top: `${ly - size * 0.62}px`, ...(side === 'right' ? { left: `${x}px` } : { right: `${1080 - x}px` }), '--tone': toneVar(tone), fontSize: `${size}px` } },
    icon ? R.icon(icon, { size: size * 1.05, stroke: 1.8 }) : null, text);
  host.append(label);
  R.chan(path, 'opacity').initial = 0;
  return {
    label, path,
    show(t) {
      drawPath(R, path, t, 0.55, { ease: 'outCubic' });
      R.tween(path, t, 0.2, { opacity: 0.9 });
      R.show(label, t + 0.3, { dur: 0.5, x: side === 'right' ? 18 : -18, y: 0 });
      return this;
    },
    hide(t) {
      R.tween(path, t, 0.3, { opacity: 0 });
      R.hide(label, t, { dur: 0.3, y: 0 });
      return this;
    },
  };
}

/** A glowing dashed path along which "pain" flows (dash offset animates between t0 and t1). */
export function flow(R, ov, pts, { tone = 'pink', t0, t1 = R.duration, width = 9, speed = 90 } = {}) {
  const path = h('path', { d: smooth(pts), fill: 'none', stroke: toneVar(tone), 'stroke-width': width, 'stroke-linecap': 'round', 'stroke-dasharray': '2 22', style: { filter: `drop-shadow(0 0 10px ${toneVar(tone)})` } });
  ov.append(path);
  R.chan(path, 'opacity').initial = 0;
  R.tween(path, t0, 0.5, { opacity: 0.95 });
  R.fn(t0, t1, (_p, s) => { path.style.strokeDashoffset = `${-s * speed}`; });
  return path;
}
