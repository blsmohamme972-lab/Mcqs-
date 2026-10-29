// Reel 06 · A map of black-outs. Source: Chapter 1, p 3 (Syncope and dizziness).
// One world, two regions: the black-out tree (left = not the heart, right = the heart) and the dizziness chain below it.
import { h } from '../../engine/dom.js';
import { World } from '../../engine/world.js';
import { rich } from '../../engine/components.js';

import { script } from './script.js';
export { script };

export function build(R) {
  const s = R.s;
  const at = (id, w, n = 1) => s[id].at(w, n);

  R.scene(0, 53.7, (sc) => {
    const W = new World(R, sc, { size: [2300, 4100] });

    // ------------------------------------------------------------ black-out tree
    const root = W.node('root', { kind: 'start', icon: 'moon', label: 'Black-out', tone: 'white', x: 1150, y: 140 });
    const nh = W.node('nh', { kind: 'step', icon: 'brain', label: 'Not the heart', tone: 'teal', w: 520, x: 800, y: 430 });
    const hr = W.node('hr', { kind: 'step', icon: 'heart-pulse', label: 'The heart', tone: 'pink', w: 460, x: 1500, y: 430 });

    const left = W.outline('nh', [
      { id: 'epi', icon: 'zap', label: 'Epilepsy' },
      { id: 'tia', icon: 'brain', label: 'TIAs' },
      { id: 'sug', icon: 'droplet', label: 'Low blood sugar' },
      { id: 'vv', icon: 'trending-down', label: 'Vasovagal faint' },
    ], { tone: 'teal', x: 560, gap: 22 });
    const vv = W.n('vv');
    const trig = W.outline('vv', [
      { id: 'tg1', icon: 'person-standing', label: 'Standing' },
      { id: 'tg2', icon: 'frown', label: 'Emotion' },
      { id: 'tg3', icon: 'wind', label: 'Coughing' },
      { id: 'tg4', icon: 'toilet', label: 'Passing urine' },
    ], { kind: 'tag', tone: 'teal', x: vv.box.x + 110, trunk: 44, gap: 14 });
    const tgEdges = trig.edges;

    const when = W.node('when', { kind: 'decision', icon: 'clock', label: 'When does it happen?', tone: 'pink', x: 1500, y: 690 });
    const as = W.node('as', { kind: 'chip', icon: 'funnel', label: 'Aortic stenosis', tone: 'pink', x: 1290, y: 960 });
    const arr = W.node('arr', { kind: 'chip', icon: 'activity', label: 'Arrhythmia', tone: 'pink', x: 1780, y: 960 });

    // ------------------------------------------------------------ dizziness chain
    const dz = W.node('dz', { kind: 'start', icon: 'tornado', label: 'Dizziness', tone: 'violet', x: 1130, y: 1740 });
    const dzA = W.node('dzA', { kind: 'tag', icon: 'arrow-right', label: 'Before a faint', tone: 'violet' });
    const dzB = W.node('dzB', { kind: 'tag', icon: 'circle-help', label: 'Fairly non-specific', tone: 'warn' });
    const tx = dz.box.x + dz.w + 90;
    dzA.place(tx + dzA.w / 2, 1700);
    dzB.place(tx + dzB.w / 2, 1790);

    const drugs = W.node('drugs', { kind: 'step', icon: 'pill', label: 'Drugs', tone: 'violet', w: 560, x: 1130, y: 2010 });
    const dOut = W.outline('drugs', ['Antianginals', 'Antihypertensives', 'Diuretics'].map((l, i) => ({ id: `d${i}`, icon: ['heart-pulse', 'gauge', 'droplets'][i], label: l })), { tone: 'violet', gap: 20, x: 900 });
    const dchips = dOut.nodes;
    const ph = W.node('ph', { kind: 'end', icon: 'trending-down', label: 'Postural hypotension', tone: 'violet', x: 1130, y: dOut.bottom + 130 });
    const trunkX = Math.max(ph.box.x + ph.w, ...dchips.map((n) => n.box.x + n.w)) + 70;

    const lowco = W.node('lowco', { kind: 'step', icon: 'gauge', label: 'Low cardiac output', tone: 'violet', w: 720, x: 1130, y: 3010 });
    const lchips = ['Failure', 'Arrhythmia', 'Ischemia'].map((l, i) => W.node(`l${i}`, { kind: 'chip', icon: ['heart-crack', 'activity', 'droplet-off'][i], label: l, tone: 'violet', cls: 'sm' }));
    let rx = 1130 - (lchips.reduce((a, n) => a + n.w, 0) + 24 * 2) / 2;
    lchips.forEach((n) => { n.place(rx + n.w / 2, 3210); rx += n.w + 24; });
    const cvd = W.node('cvd', { kind: 'step', icon: 'brain', label: 'Cerebrovascular disease', tone: 'violet', w: 800, x: 1130, y: 3440 });

    const dan = W.node('dan', { kind: 'step', icon: 'syringe', label: 'Diabetic autonomic neuropathy', tone: 'violet', w: 940, x: 1130, y: 3770 });
    const under = W.node('under', { kind: 'tag', icon: 'circle-help', label: 'Probably under-recognized', tone: 'warn', x: 1130, y: 3910 });

    // ------------------------------------------------------------ districts
    const zNh = W.zone(['nh', 'epi', 'tia', 'sug', 'vv', 'tg1', 'tg2', 'tg3', 'tg4'], { tone: 'teal', label: 'Not the heart' });
    const zHr = W.zone(['hr', 'when', 'as', 'arr'], { tone: 'pink', label: 'The heart' });
    const zDz = W.zone(['dz', 'dzA', 'dzB'], { tone: 'violet', label: 'Dizziness' });
    const zDr = W.zone(['drugs', 'd0', 'd1', 'd2', 'ph'], { tone: 'violet', label: 'Drugs' });
    const zLo = W.zone(['lowco', 'l0', 'l1', 'l2', 'cvd'], { tone: 'violet', label: 'Output and vessels' });
    const zDa = W.zone(['dan', 'under'], { tone: 'violet', label: 'Autonomic' });

    // ------------------------------------------------------------ edges
    const e = {
      r1: W.edge(root, nh, { bend: 290 }),
      r2: W.edge(root, hr, { bend: 290 }),
      hw: W.edge(hr, when),
      wa: W.edge(when, as, { label: 'exertional', labelAt: 0.86 }),
      wr: W.edge(when, arr, { label: 'sitting or lying', labelAt: 0.86 }),
      dzA: W.edge(dz, dzA, { from: 'r', to: 'l', tone: 'violet', arrowSize: 11 }),
      dzB: W.edge(dz, dzB, { from: 'r', to: 'l', tone: 'warn', arrowSize: 11 }),
      dzDrugs: W.edge(dz, drugs, { tone: 'violet' }),
      dc: dOut.edges,
      dp: dchips.map((n) => W.edge(n, ph, { from: 'r', to: 'r', via: [[trunkX, n.y], [trunkX, ph.y]], tone: 'violet', arrowSize: 12 })),
      dl: W.edge(ph, lowco, { tone: 'violet' }),
      lc: lchips.map((n) => W.edge(lowco, n, { tone: 'violet' })),
      lcv: W.edge(lchips[1], cvd, { tone: 'violet' }),
      cd: W.edge(cvd, dan, { tone: 'violet' }),
      du: W.edge(dan, under, { tone: 'warn' }),
    };

    // ------------------------------------------------------------ choreography
    const appear = (n, ed, t, hold = 1.3) => W.appear(n, ed, t, { hold });
    const nhCluster = ['nh', 'epi', 'tia', 'sug', 'vv', 'tg1', 'tg4'];

    // hook: black-out → not always the heart
    W.start(['root', 'nh', 'hr'], { max: 1 });
    appear(root, null, at('hook', 'blackout') - 0.1, 2.2);
    appear(hr, e.r2, at('hook', 'not'), 0.9);
    appear(nh, e.r1, at('hook', 'always'), 0.9);

    // not the heart
    W.go(at('nonc', 'think') - 0.45, 'nh', { dur: 1.2, fit: zNh, max: 1.5, pad: 44 });
    zNh.in(at('nonc', 'epilepsy') - 0.5);
    [['epilepsy', 0], ['tias', 1], ['low blood sugar', 2], ['vasovagal', 3]].forEach(([w, i]) => appear(left.nodes[i], left.edges[i], at('nonc', w) - 0.1));
    left.nodes[3].lit(at('vv', 'vasovagal'), 1, 0.4);
    [['standing', 0], ['emotion', 1], ['coughing', 2], ['passing urine', 3]].forEach(([w, i]) => appear(trig.nodes[i], tgEdges[i], at('vv', w) - 0.1, 1.0));
    left.nodes[3].lit(at('vv', 'urine') + 1.0, 0.45, 0.7);

    // the heart
    W.go(at('cardiac', 'true') - 0.35, 'hr', { dur: 1.3, fit: zHr, max: 1.5, pad: 44 });
    zHr.in(at('cardiac', 'true') - 0.1);
    appear(when, e.hw, at('cardiac', 'syncope') - 0.1, 3.2);
    appear(as, e.wa, at('cardiac', 'aortic') - 0.1, 99);
    appear(arr, e.wr, at('arr', 'sitting') - 0.1, 99);
    as.lit(at('cardiac', 'exertional'), 1, 0.3).pop(at('cardiac', 'exertional'));
    arr.lit(at('arr', 'arrhythmia'), 1, 0.3).pop(at('arr', 'arrhythmia'));
    as.lit(at('arr', 'if'), 0.4, 0.6);

    // dizziness
    W.go(at('dizzy', 'dizziness') - 0.45, 'dz', { dur: 1.6, fit: zDz, max: 1.9, pad: 44 });
    zDz.in(at('dizzy', 'dizziness') - 0.35);
    appear(dz, null, at('dizzy', 'dizziness') - 0.1, 99);
    appear(dzA, e.dzA, at('dizzy', 'before') - 0.2, 99);
    appear(dzB, e.dzB, at('dizzy', 'fairly') - 0.2, 99);

    W.go(at('drugs', 'common') - 0.3, 'drugs', { dur: 1.2, fit: zDr, max: 1.7, pad: 44 });
    zDr.in(at('drugs', 'drugs') - 0.5);
    appear(drugs, e.dzDrugs, at('drugs', 'drugs') - 0.2, 99);
    dchips.forEach((n, i) => appear(n, e.dc[i], at('drugs', ['antianginals', 'antihypertensives', 'diuretics'][i]) - 0.1, 99));
    e.dp.forEach((ed, i) => ed.in(at('drugs', 'causing') - 0.1 + i * 0.12, 0.6));
    appear(ph, null, at('drugs', 'postural') - 0.1, 99);
    dchips.forEach((n) => n.lit(at('drugs', 'hypotension') + 1, 0.4, 0.5));

    W.go(at('low', 'low') - 0.5, 'lowco', { dur: 1.3, fit: zLo, max: 1.5, pad: 44 });
    zLo.in(at('low', 'low') - 0.4);
    appear(lowco, e.dl, at('low', 'low') - 0.2, 99);
    lchips.forEach((n, i) => appear(n, e.lc[i], at('low', ['failure', 'arrhythmia', 'ischemia'][i]) - 0.1, 99));
    appear(cvd, e.lcv, at('low', 'cerebrovascular') - 0.2, 99);

    W.go(at('diab', 'diabetic') - 0.5, 'dan', { dur: 1.2, fit: zDa, max: 1.9, pad: 44 });
    zDa.in(at('diab', 'diabetic') - 0.4);
    appear(dan, e.cd, at('diab', 'diabetic') - 0.2, 99);
    appear(under, e.du, at('diab', 'underrecognized') - 0.3, 99);
    W.finish();
  }, { drift: 0, exit: { y: 0 } });

  // ---------------------------------------------------------------- recap
  R.scene(53.35, 60, (sc) => {
    const rows = [
      ['clock', 'pink', 'When did it *happen?*', 'Exertional · sitting or lying', s.rec.at('when'), 330],
      ['person-standing', 'teal', 'What were they *doing?*', 'Standing · emotion · coughing · urine', s.rec.at('what', 1), 700],
      ['pill', 'violet', 'What are they *taking?*', 'Antianginals · antihypertensives · diuretics', s.rec.at('what', 2), 1070],
    ];
    rows.forEach(([ic, tone, q, sub, t, y]) => {
      const tile = h('div', { class: 'abs ic-tile', style: { left: '72px', top: `${y}px`, '--tone': `var(--${tone})` } }, R.icon(ic, { size: 72, stroke: 1.7 }));
      const rq = rich(R, q, { cls: 'serif m', style: { position: 'absolute', left: '230px', top: `${y - 6}px`, width: '780px' } });
      const sb = h('div', { class: 'abs body', style: { left: '234px', top: `${y + 156}px`, width: '770px' } }, sub);
      sc.add(tile, rq.el, sb);
      R.show(tile, t - 0.1, { dur: 0.6, y: 30, scale: 0.85 });
      rq.reveal(t - 0.05, 0.09);
      R.show(sb, t + 0.5, { dur: 0.6, y: 14 });
    });
  }, { exit: false, drift: 0 });
}
