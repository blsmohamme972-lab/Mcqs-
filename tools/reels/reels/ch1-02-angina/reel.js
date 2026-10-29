// Reel 02 · The angina pathway. Source: Chapter 1, p 2 (Angina) and Box 1.1 (CCS classes).
// Five stations on one route: describe it, trigger it, relieve it, count it, grade it.
import { World, chip } from '../../engine/world.js';
import { body, LM, hotspot, flow } from '../../engine/body.js';
import { thresholdBars, dayStrip } from '../../engine/charts.js';
import { h } from '../../engine/dom.js';

import { script } from './script.js';
export { script };

export function build(R) {
  const s = R.s;
  const at = (id, w, n = 1) => s[id].at(w, n);

  R.scene(0, 54.1, (sc) => {
    const W = new World(R, sc, { size: [1080, 5000] });
    const L = 110; // left edge of station content

    // ---------------------------------------------------------------- hook
    const angina = W.node('angina', { kind: 'start', icon: 'heart-pulse', label: 'Angina', tone: 'pink', x: 540, y: 170 });
    const notAlways = W.node('na', { kind: 'tag', icon: 'triangle-alert', label: 'is not always', tone: 'warn', x: 540, y: 330 });
    const crush = W.node('crush', { kind: 'chip', icon: 'heart-crack', label: 'Crushing chest pain', tone: 'pink', x: 540, y: 480 });

    // ---------------------------------------------------------------- 1 · describe
    const y1 = 760, bs = 0.62;
    const d1 = W.node('d1', { kind: 'step', icon: 'message-square-text', label: 'Describe it', tone: 'white', num: 1, w: 520, x: L + 260, y: y1 });
    const B = body(R, { x: 90, y: y1 + 100, scale: bs, id: 'bd' });
    W.el.append(B.svg);
    R.chan(B.svg, 'opacity').initial = 0;
    R.chan(B.svg, 'css:--g', { initial: 0 });
    const colX = 470, col0 = y1 + 215;
    const hdr = (id, label, tone) => W.node(id, { kind: 'note', label, tone, cls: 'hdr', x: colX + 110, y: y1 + 150 });
    const hTb = hdr('hTb', 'TEXTBOOK', 'pink');
    const hAt = hdr('hAt', 'ATYPICAL', 'violet');
    const stack = (specs, tone) => {
      let cy = col0;
      return specs.map((sp) => {
        const n = W.node(sp.id, { kind: 'chip', ...sp, tone, cls: 'sm' });
        n.place(colX + n.w / 2, cy + n.h / 2);
        cy += n.h + 16;
        return n;
      });
    };
    const tb = stack([
      { id: 'tb1', icon: 'heart-crack', label: 'Central, crushing' },
      { id: 'tb2', icon: 'smile', label: 'Jaw' },
      { id: 'tb3', icon: 'hand', label: 'Left arm' },
    ], 'pink');
    const at5 = stack([
      { id: 'at1', icon: 'weight', label: 'Heaviness' },
      { id: 'at2', icon: 'utensils', label: 'Indigestion' },
      { id: 'at3', icon: 'move-diagonal', label: 'Arm, neck or jaw only' },
      { id: 'at4', icon: 'frown', label: 'Nausea' },
      { id: 'at5', icon: 'battery-low', label: 'Fatigue' },
    ], 'violet');
    const bodyRect = { x: 90, y: y1 + 100, w: 560 * bs, h: 1080 * bs };
    const z1 = W.zone(['d1', 'hTb', 'hAt', 'tb1', 'tb2', 'tb3', 'at1', 'at2', 'at3', 'at4', 'at5'], { tone: 'pink', label: 'Pain pattern', extra: [bodyRect] });

    // ---------------------------------------------------------------- 2 · trigger
    const y2 = z1.rect.y + z1.rect.h + 210;
    const d2 = W.node('d2', { kind: 'step', icon: 'zap', label: 'What brings it on?', tone: 'white', num: 2, w: 700, x: L + 350, y: y2 });
    const trg = W.outline('d2', [
      { id: 'tr1', icon: 'footprints', label: 'Exertion' },
      { id: 'tr2', icon: 'brain', label: 'Stress' },
      { id: 'tr3', icon: 'frown', label: 'Emotion' },
      { id: 'tr4', icon: 'snowflake', label: 'Cold air' },
    ], { tone: 'teal', x: L + 70, gap: 18 });
    const z2 = W.zone(['d2', 'tr1', 'tr2', 'tr3', 'tr4'], { tone: 'teal', label: 'Precipitants' });

    // ---------------------------------------------------------------- 3 · relieve
    const y3 = z2.rect.y + z2.rect.h + 200;
    const d3 = W.node('d3', { kind: 'step', icon: 'heart-handshake', label: 'What relieves it?', tone: 'white', num: 3, w: 700, x: L + 350, y: y3 });
    const rel = W.outline('d3', [
      { id: 'rl1', icon: 'armchair', label: 'Rest' },
      { id: 'rl2', icon: 'pill', label: 'Sublingual nitroglycerine' },
    ], { tone: 'violet', x: L + 70, gap: 18 });
    const z3 = W.zone(['d3', 'rl1', 'rl2'], { tone: 'violet', label: 'Relievers' });

    // ---------------------------------------------------------------- 4 · count
    const y4 = z3.rect.y + z3.rect.h + 200;
    const d4 = W.node('d4', { kind: 'step', icon: 'hash', label: 'Count the spray', tone: 'white', num: 4, w: 620, x: L + 310, y: y4 });
    const strip = dayStrip(R, { w: 820, doses: [4, 8, 12, 17, 21], icon: 'spray-can', tone: 'pink', label: '×' });
    W.put(strip.el, { x: L, y: y4 + 100, anchor: 'tl' });
    const sprayNote = W.node('sn', { kind: 'tag', icon: 'spray-can', label: 'NTG spray, times per day', tone: 'pink', x: L + 410, y: y4 + 470 });
    const z4 = W.zone(['d4', 'sn'], { tone: 'pink', label: 'Frequency', extra: [{ x: L, y: y4 + 100, w: 820, h: 330 }] });

    // ---------------------------------------------------------------- 5 · grade
    const y5 = z4.rect.y + z4.rect.h + 200;
    const d5 = W.node('d5', { kind: 'step', icon: 'signal-high', label: 'Grade it', tone: 'white', num: 5, w: 480, x: L + 240, y: y5 });
    const ccs = W.node('ccs', { kind: 'tag', icon: 'info', label: 'CCS · angina only', tone: 'warn', x: L + 640, y: y5 });
    const bars = thresholdBars(R, {
      w: 880, rowH: 172,
      rows: [
        { numeral: 'I', text: 'No angina with ordinary activity', thr: 0.84 },
        { numeral: 'II', text: 'Slight limitation', thr: 0.54 },
        { numeral: 'III', text: 'Marked limitation', thr: 0.32 },
        { numeral: 'IV', text: 'Minimal exertion or at rest', thr: 0.09 },
      ],
    });
    W.put(bars.el, { x: L - 10, y: y5 + 110, anchor: 'tl' });
    const risk = W.node('risk', { kind: 'end', icon: 'triangle-alert', label: 'Increased risk', tone: 'serious', x: L + 640, y: y5 + 110 + bars.height + 70 });
    const z5 = W.zone(['d5', 'ccs', 'risk'], { tone: 'pink', label: 'CCS classes', extra: [{ x: L - 10, y: y5 + 110, w: 880, h: bars.height }] });

    // ---------------------------------------------------------------- edges (the route)
    const e = {
      a1: W.edge(angina, notAlways, { tone: 'warn' }),
      a2: W.edge(notAlways, crush, { tone: 'pink' }),
      t: trg.edges, r: rel.edges,
      s12: W.edge(d1, d2, { from: 'l', to: 'l', via: [[64, d1.y], [64, d2.y]], tone: 'white', arrowSize: 14 }),
      s23: W.edge(d2, d3, { from: 'l', to: 'l', via: [[64, d2.y], [64, d3.y]], tone: 'white', arrowSize: 14 }),
      s34: W.edge(d3, d4, { from: 'l', to: 'l', via: [[64, d3.y], [64, d4.y]], tone: 'white', arrowSize: 14 }),
      s45: W.edge(d4, d5, { from: 'l', to: 'l', via: [[64, d4.y], [64, d5.y]], tone: 'white', arrowSize: 14 }),
    };

    // ---------------------------------------------------------------- choreography
    const appear = (n, ed, t, hold = 1.3) => W.appear(n, ed, t, { hold });
    const popT = (n, t) => n.lit(t, 1, 0.3).pop(t);

    // hook
    W.start('angina', { zoom: 1.0 });
    appear(angina, null, at('hook', 'angina') - 0.15, 99);
    appear(notAlways, e.a1, at('hook', 'not') - 0.15, 99);
    appear(crush, e.a2, at('hook', 'crushing') - 0.2, 99);

    // 1 · describe
    W.go(at('classic', 'textbook') - 0.45, 'd1', { dur: 1.3, fit: z1, max: 1.1, pad: 44 });
    z1.in(at('classic', 'textbook') - 0.3);
    appear(d1, e.a2, at('classic', 'textbook') - 0.2, 99);
    R.show(B.svg, at('classic', 'textbook') - 0.1, { dur: 0.9, y: 0 });
    appear(hTb, null, at('classic', 'textbook') + 0.1, 99);
    appear(tb[0], null, at('classic', 'central') - 0.1, 99);
    appear(tb[1], null, at('classic', 'jaw') - 0.1, 99);
    appear(tb[2], null, at('classic', 'left') - 0.1, 99);
    const heartPt = B.pt(LM.heart), jawPt = B.pt(LM.jaw), armPt = B.pt(LM.leftArm), wristPt = B.pt(LM.leftWrist);
    const hsC = hotspot(R, W.el, heartPt, { t0: at('classic', 'central'), tone: 'pink' });
    const hsJ = hotspot(R, W.el, jawPt, { t0: at('classic', 'jaw'), tone: 'pink', size: 26, core: 10 });
    const hsA = hotspot(R, W.el, armPt, { t0: at('classic', 'left'), tone: 'pink', size: 26, core: 10 });
    const fJ = flow(R, W.svg, [heartPt, B.pt([LM.heart[0] - 6, 300]), B.pt([LM.neck[0] + 20, 232]), jawPt], { t0: at('classic', 'jaw') - 0.1, tone: 'pink' });
    const fA = flow(R, W.svg, [heartPt, B.pt([LM.heart[0] + 70, 330]), B.pt(LM.leftShoulder), armPt, wristPt], { t0: at('classic', 'left') - 0.1, tone: 'pink' });
    // atypical: the textbook picture steps aside and violet spots take over the same column
    const tAty = at('atyp', 'but');
    [hsC, hsJ, hsA].forEach((el) => R.hide(el, tAty - 0.1, { dur: 0.5, y: 0 }));
    [fJ, fA].forEach((el) => R.hide(el, tAty - 0.1, { dur: 0.5, y: 0 }));
    [hTb, ...tb].forEach((n) => n.out(tAty - 0.1, { dur: 0.45 }));
    appear(hAt, null, tAty + 0.25, 99);
    const spots = [
      [at('atyp', 'heaviness'), B.pt([LM.chest[0], 392]), 34, 12],
      [at('atyp', 'indigestion'), B.pt(LM.epigastrium), 28, 10],
      [at('atyp', 'arm', 1), B.pt(LM.leftArm), 24, 9],
      [at('atyp', 'neck'), B.pt(LM.carotid), 22, 9],
      [at('atyp', 'jaw'), B.pt(LM.jaw), 22, 9],
      [at('atyp', 'nausea'), B.pt([LM.head[0], 150]), 26, 10],
    ];
    spots.forEach(([t, p, sz, core]) => hotspot(R, W.el, p, { t0: t - 0.05, tone: 'violet', size: sz, core }));
    appear(at5[0], null, at('atyp', 'heaviness') - 0.1, 99);
    appear(at5[1], null, at('atyp', 'indigestion') - 0.1, 99);
    appear(at5[2], null, at('atyp', 'pain') - 0.1, 99);
    appear(at5[3], null, at('atyp', 'nausea') - 0.1, 99);
    appear(at5[4], null, at('atyp', 'fatigue') - 0.1, 99);
    R.tween(B.svg, at('atyp', 'fatigue') - 0.1, 0.8, { 'css:--g': 1 }, { ease: 'outCubic' });

    // 2 · trigger
    W.go(at('trig', 'so') - 0.45, 'd2', { dur: 1.3, fit: z2, max: 1.5, pad: 44 });
    z2.in(at('trig', 'so') - 0.3);
    appear(d2, e.s12, at('trig', 'ask') - 0.2, 99);
    [['exertion', 0], ['stress', 1], ['emotion', 2], ['cold', 3]].forEach(([w, i]) => appear(trg.nodes[i], trg.edges[i], at('trig', w) - 0.1, 1.2));

    // 3 · relieve
    W.go(at('rel', 'and') - 0.45, 'd3', { dur: 1.3, fit: z3, max: 1.6, pad: 44 });
    z3.in(at('rel', 'and') - 0.3);
    appear(d3, e.s23, at('rel', 'relieves') - 0.3, 99);
    appear(rel.nodes[0], rel.edges[0], at('rel', 'rest') - 0.1, 1.2);
    appear(rel.nodes[1], rel.edges[1], at('rel', 'sublingual') - 0.1, 99);

    // 4 · count
    W.go(at('spray', 'then') - 0.45, 'd4', { dur: 1.3, fit: z4, max: 1.3, pad: 44 });
    z4.in(at('spray', 'then') - 0.3);
    appear(d4, e.s34, at('spray', 'count') - 0.3, 99);
    R.show(strip.el, at('spray', 'spray') - 0.1, { dur: 0.7, y: 20 });
    const doseT = [at('spray', 'how'), at('spray', 'many'), at('spray', 'times'), at('spray', 'day'), at('spray', 'need')];
    doseT.forEach((t, i) => strip.dose(i, t));
    strip.counter(doseT);
    appear(sprayNote, null, at('spray', 'many') - 0.2, 99);

    // 5 · grade
    W.go(at('grade', 'finally') - 0.45, 'd5', { dur: 1.4, fit: z5, max: 1.1, pad: 44 });
    z5.in(at('grade', 'finally') - 0.3);
    appear(d5, e.s45, at('grade', 'grade') - 0.25, 99);
    appear(ccs, null, at('grade', 'canadian') - 0.1, 99);
    bars.axisIn(at('grade', 'scale') - 0.2);
    bars.rows[0].in(at('c12', 'class', 1) - 0.1).fill(at('c12', 'no') - 0.05).hl(at('c12', 'no'), 1).hl(at('c12', 'activity') + 0.8, 0);
    bars.rows[1].in(at('c12', 'class', 2) - 0.1).fill(at('c12', 'slight') - 0.05).hl(at('c12', 'slight'), 1).hl(at('c34', 'class', 1) - 0.1, 0);
    bars.rows[2].in(at('c34', 'class', 1) - 0.1).fill(at('c34', 'marked') - 0.05).hl(at('c34', 'marked'), 1).hl(at('c34', 'class', 2) - 0.1, 0);
    bars.rows[3].in(at('c34', 'class', 2) - 0.1).fill(at('c34', 'angina') - 0.05).hl(at('c34', 'angina'), 1);
    bars.rows[2].hl(at('risk', 'three'), 1);
    bars.rows[3].hl(at('risk', 'four'), 1);
    appear(risk, null, at('risk', 'increased') - 0.2, 99);

    W.finish();
  }, { drift: 0, exit: { y: 0 } });

  // ---------------------------------------------------------------- recap: the five-step route
  R.scene(53.8, 60, (sc) => {
    const W = new World(R, sc, { size: [1080, 1300], grid: false });
    const steps = [
      ['message-square-text', 'Describe it', 'describe', 'pink'],
      ['zap', 'Trigger it', 'trigger', 'teal'],
      ['heart-handshake', 'Relieve it', 'relieve', 'violet'],
      ['hash', 'Count it', 'count', 'pink'],
      ['signal-high', 'Grade it', 'grade', 'teal'],
    ];
    const ns = steps.map(([icon, label, , tone], i) => W.node(`r${i}`, { kind: 'step', icon, label, tone, num: i + 1, w: 640, x: 540, y: 190 + i * 205 }));
    W.start([0, 0], { zoom: 1, anchor: [0, 0] });
    R.chan(W.el, 'x').initial = 0; R.chan(W.el, 'y').initial = 0; R.chan(W.el, 'scale').initial = 1;
    steps.forEach(([, , cue], i) => {
      const t = s.rec.at(cue) - 0.05;
      W.appear(ns[i], i ? W.edge(ns[i - 1], ns[i], { tone: steps[i][3] }) : null, t, { hold: 99 });
      if (i) ns[i - 1].lit(t + 0.1, 0.5, 0.5);
    });
  }, { exit: false, drift: 0 });
}
