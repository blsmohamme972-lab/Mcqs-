// Reel 07 · What a palpitation feels like, and what the onset tells you. Source: Chapter 1, p 3 (Palpitations and AF; Peripheral edema).
// ECG strips are drawn live from a rate function, so the rhythm changes exactly when the narrator says it does.
import { World } from '../../engine/world.js';
import { body, LM, hotspot } from '../../engine/body.js';
import { beats, ecgStrip } from '../../engine/ecg.js';
import { h } from '../../engine/dom.js';
import { clamp } from '../../engine/core.js';

import { script } from './script.js';
export { script };

const smooth01 = (x) => { const t = clamp(x); return t * t * (3 - 2 * t); };

export function build(R) {
  const s = R.s;
  const at = (id, w, n = 1) => s[id].at(w, n);

  R.scene(0, 52.6, (sc) => {
    const W = new World(R, sc, { size: [1080, 4300] });
    const L = 110;

    // ---------------------------------------------------------------- hook
    const pal = W.node('pal', { kind: 'start', icon: 'heart-pulse', label: 'Palpitation', tone: 'pink', x: 540, y: 170 });
    const q = W.node('q', { kind: 'tag', icon: 'circle-help', label: 'what does it feel like?', tone: 'white', x: 540, y: 340 });

    // ---------------------------------------------------------------- 1 · what it feels like (four rhythms)
    const rows = [
      { id: 'c1', icon: 'skip-forward', label: 'Skipped beats', cue: 'skipped', bs: beats(() => 76, { omit: [8.15, 11.4] }), p: true },
      { id: 'c2', icon: 'rabbit', label: 'Racing heart', cue: 'racing', bs: beats(() => 152, { seed: 3 }), p: true },
      { id: 'c3', icon: 'shuffle', label: 'Irregular rhythm', cue: 'irregular', bs: beats(() => 82, { jitter: 0.6, seed: 11 }), p: true },
      { id: 'c4', icon: 'heart', label: 'Aware of the heartbeat', cue: 'awareness', bs: beats(() => 62, { seed: 5 }), p: true },
    ];
    const y0 = 560, pitch = 228;
    rows.forEach((r, i) => {
      r.chip = W.node(r.id, { kind: 'chip', icon: r.icon, label: r.label, tone: 'teal', cls: 'sm', x: 0, y: 0 });
      r.chip.place(L + r.chip.w / 2, y0 + i * pitch);
      r.strip = ecgStrip(R, { w: 860, h: 150, bs: r.bs, tone: 'teal', p: r.p });
      W.put(r.strip.el, { x: L - 10, y: y0 + i * pitch + 54, anchor: 'tl' });
    });
    const night = W.node('night', { kind: 'tag', icon: 'moon', label: 'especially at night', tone: 'violet', x: 0, y: 0 });
    night.place(rows[3].chip.box.x + rows[3].chip.w + 24 + night.w / 2, rows[3].chip.y);
    const z1 = W.zone(['c1', 'c2', 'c3', 'c4', 'night'], { tone: 'teal', label: 'What the patient feels', extra: rows.map((r, i) => ({ x: L - 10, y: y0 + i * pitch + 54, w: 860, h: 150, t: at('feel', r.cue) - 0.15 })) });

    // ---------------------------------------------------------------- 2 · onset and offset
    const yD = z1.rect.y + z1.rect.h + 260;
    const dec = W.node('dec', { kind: 'decision', icon: 'timer', label: 'Onset and offset?', tone: 'white', x: 540, y: yD });

    const rateA = (t) => 72 + 96 * (((t > 19.4 && t < 20.35) || (t > 24.2 && t < 25.3)) ? 1 : 0);
    const rateB = (t) => 72 + 70 * (smooth01((t - 26.0) / 2.4) - smooth01((t - 30.3) / 1.8));
    const panel = (key, tone, yTop, chipSpec, endSpec, rate, seed, tStrip) => {
      const chip = W.node(`${key}c`, { kind: 'chip', ...chipSpec, tone, cls: 'sm' });
      chip.place(L + chip.w / 2, yTop);
      const strip = ecgStrip(R, { w: 860, h: 170, bs: beats(rate, { seed }), tone });
      W.put(strip.el, { x: L - 10, y: yTop + 56, anchor: 'tl' });
      const bpm = h('div', { class: 'bpm', style: { '--tone': `var(--${tone})` } }, h('b', {}, '72'), h('span', {}, 'bpm'));
      W.put(bpm, { x: 0, y: yTop - 30, anchor: 'tl' });
      bpm.style.left = `${L + 860 - 10 - bpm.offsetWidth}px`;
      strip.rate(rate, bpm.querySelector('b'));
      R.chan(bpm, 'opacity').initial = 0;
      const end = W.node(`${key}e`, { kind: 'end', ...endSpec, tone });
      end.place(L + end.w / 2, yTop + 56 + 170 + 78);
      const zone = W.zone([`${key}c`, `${key}e`], { tone, label: key === 'a' ? 'Switches on and off' : 'Fades in and out', extra: [{ x: L - 10, y: yTop + 56, w: 860, h: 170, t: tStrip }, { x: L, y: yTop - 60, w: 860, h: 60, t: tStrip }] });
      return { chip, strip, bpm, end, zone };
    };
    const pa = panel('a', 'pink', yD + 330, { icon: 'zap', label: 'Rapid onset and offset' }, { icon: 'activity', label: 'Paroxysmal arrhythmia' }, rateA, 21, at('rapid', 'onset') - 0.35);
    const pb = panel('b', 'violet', pa.zone.rect.y + pa.zone.rect.h + 250, { icon: 'trending-up', label: 'Gradual onset and offset' }, { icon: 'heart-pulse', label: 'Sinus tachycardia' }, rateB, 33, at('grad', 'onset') - 0.35);

    // ---------------------------------------------------------------- 3 · atrial fibrillation
    const yAf = pb.zone.rect.y + pb.zone.rect.h + 300;
    const af = W.node('af', { kind: 'step', icon: 'activity', label: 'Preoperative AF', tone: 'pink', w: 620, x: 540, y: yAf });
    const afStrip = ecgStrip(R, { w: 860, h: 150, bs: beats(() => 118, { jitter: 0.55, seed: 7 }), tone: 'pink', p: false, fib: true });
    W.put(afStrip.el, { x: L - 10, y: yAf + 100, anchor: 'tl' });
    const mayNeed = W.node('may', { kind: 'note', cls: 'hdr', label: 'MAY NEED', tone: 'teal', x: 540, y: yAf + 300 });
    const afList = W.outline('af', [
      { id: 'ab', icon: 'zap', label: 'Ablation' },
      { id: 'la', icon: 'scissors', label: 'Left atrial appendage ligation' },
      { id: 'wf', icon: 'pill', label: 'Warfarin' },
    ], { tone: 'teal', x: L + 60, y: yAf + 340, gap: 18 });
    const zAf = W.zone(['af', 'may', 'ab', 'la', 'wf'], { tone: 'pink', label: 'Atrial fibrillation', extra: [{ x: L - 10, y: yAf + 100, w: 860, h: 150, t: at('af', 'atrial') - 0.3 }] });

    // ---------------------------------------------------------------- 4 · edema
    const yEd = zAf.rect.y + zAf.rect.h + 300;
    const ed = W.node('ed', { kind: 'step', icon: 'waves', label: 'Peripheral edema', tone: 'violet', w: 620, x: 540, y: yEd });
    const B = body(R, { x: 100, y: yEd + 120, scale: 0.46, id: 'bdE' });
    W.el.append(B.svg);
    R.chan(B.svg, 'opacity').initial = 0;
    const causes = W.outline('ed', [
      { id: 'e1', icon: 'droplets', label: 'Diuretic changes' },
      { id: 'e2', icon: 'scale', label: 'Weight gain' },
      { id: 'e3', icon: 'wind', label: 'Worse dyspnea' },
    ], { tone: 'violet', x: 470, y: yEd + 170, gap: 20 });
    const quant = W.node('quant', { kind: 'end', icon: 'ruler', label: 'Quantifies the heart failure', tone: 'violet', x: 540, y: yEd + 120 + 1080 * 0.46 + 90 });
    const zEd = W.zone(['ed', 'e1', 'e2', 'e3', 'quant'], { tone: 'violet', label: 'Swelling', extra: [{ x: 100, y: yEd + 120, w: 560 * 0.46, h: 1080 * 0.46, t: at('edema', 'now') - 0.2 }] });

    // ---------------------------------------------------------------- edges
    const e = {
      pq: W.edge(pal, q, { tone: 'white' }),
      da: W.edge(dec, pa.chip, { tone: 'pink' }),
      db: W.edge(dec, pb.chip, { from: 'l', to: 'l', via: [[64, dec.y], [64, pb.chip.y]], tone: 'violet', arrowSize: 14 }),
      ae: W.edge(pa.chip, pa.end, { from: 'l', to: 'l', via: [[L - 46, pa.chip.y], [L - 46, pa.end.y]], tone: 'pink', arrowSize: 13 }),
      be: W.edge(pb.chip, pb.end, { from: 'l', to: 'l', via: [[L - 46, pb.chip.y], [L - 46, pb.end.y]], tone: 'violet', arrowSize: 13 }),
      qe: W.edge(ed, quant, { from: 'l', to: 'l', via: [[70, ed.y], [70, quant.y]], tone: 'violet', arrowSize: 14 }),
    };

    // ---------------------------------------------------------------- choreography
    const appear = (n, ed2, t, hold = 1.3) => W.appear(n, ed2, t, { hold });

    W.start('pal', { zoom: 1.25 });
    appear(pal, null, at('hook', 'palpitation') - 0.2, 99);
    appear(q, e.pq, at('hook', 'actually') - 0.3, 99);

    // 1 · feel
    W.go(at('feel', 'to') - 0.5, 'c1', { dur: 1.4, fit: z1, max: 1.15, pad: 44 });
    z1.in(at('feel', 'skipped') - 0.6);
    rows.forEach((r) => { r.strip.in(at('feel', r.cue) - 0.15); appear(r.chip, null, at('feel', r.cue) - 0.2, 99); });
    appear(night, null, at('feel', 'especially') - 0.1, 99);

    // 2 · onset and offset
    W.go(at('onset', 'then') - 0.45, 'dec', { dur: 1.4, zoom: 1.25 });
    appear(dec, null, at('onset', 'onset') - 0.25, 99);
    W.go(at('rapid', 'rapid') - 0.5, 'ac', { dur: 1.3, fit: pa.zone, max: 1.15, pad: 44 });
    pa.zone.in(at('rapid', 'rapid') - 0.4);
    appear(pa.chip, e.da, at('rapid', 'rapid') - 0.2, 99);
    pa.strip.in(at('rapid', 'onset') - 0.35);
    R.show(pa.bpm, at('rapid', 'onset') - 0.35, { dur: 0.6, y: 12 });
    appear(pa.end, e.ae, at('rapid', 'paroxysmal') - 0.1, 99);
    W.go(at('grad', 'gradual') - 0.5, 'bc', { dur: 1.3, fit: pb.zone, max: 1.15, pad: 44 });
    pb.zone.in(at('grad', 'gradual') - 0.4);
    appear(pb.chip, e.db, at('grad', 'gradual') - 0.2, 99);
    pb.strip.in(at('grad', 'onset') - 0.35);
    R.show(pb.bpm, at('grad', 'onset') - 0.35, { dur: 0.6, y: 12 });
    appear(pb.end, e.be, at('grad', 'sinus') - 0.1, 99);

    // 3 · AF
    W.go(at('af', 'preoperative') - 0.5, 'af', { dur: 1.4, fit: zAf, max: 1.2, pad: 44 });
    zAf.in(at('af', 'preoperative') - 0.4);
    appear(af, null, at('af', 'preoperative') - 0.2, 99);
    afStrip.in(at('af', 'atrial') - 0.3);
    appear(mayNeed, null, at('af', 'may') - 0.2, 99);
    appear(afList.nodes[0], afList.edges[0], at('af', 'ablation') - 0.15, 99);
    appear(afList.nodes[1], afList.edges[1], at('af', 'left') - 0.15, 99);
    appear(afList.nodes[2], afList.edges[2], at('af', 'warfarin') - 0.15, 99);

    // 4 · edema
    W.go(at('edema', 'now') - 0.5, 'ed', { dur: 1.4, fit: zEd, max: 1.2, pad: 44 });
    zEd.in(at('edema', 'now') - 0.4);
    R.show(B.svg, at('edema', 'now') - 0.2, { dur: 0.9, y: 0 });
    appear(ed, null, at('edema', 'peripheral') - 0.2, 99);
    hotspot(R, W.el, B.pt(LM.leftAnkle), { t0: at('edema', 'swelling'), tone: 'violet', size: 30, core: 11 });
    hotspot(R, W.el, B.pt(LM.rightAnkle), { t0: at('edema', 'swelling'), tone: 'violet', size: 30, core: 11 });
    appear(causes.nodes[0], causes.edges[0], at('edema', 'diuretic') - 0.15, 99);
    appear(causes.nodes[1], causes.edges[1], at('edema', 'weight') - 0.15, 99);
    appear(causes.nodes[2], causes.edges[2], at('edema', 'worse') - 0.15, 99);
    appear(quant, e.qe, at('quant', 'quantify') - 0.2, 99);

    W.finish();
  }, { drift: 0, exit: { y: 0 } });

  // ---------------------------------------------------------------- recap
  R.scene(52.3, 60, (sc) => {
    const W = new World(R, sc, { size: [1080, 1300], grid: false });
    const steps = [
      ['heart-pulse', 'What did it feel like?', 'what', 'teal'],
      ['timer', 'How did it start and stop?', 'how', 'pink'],
      ['waves', 'Do the ankles swell?', 'ankles', 'violet'],
    ];
    const ns = steps.map(([icon, label, , tone], i) => W.node(`r${i}`, { kind: 'step', icon, label, tone, num: i + 1, w: 860, x: 540, y: 250 + i * 270 }));
    W.start([0, 0], { zoom: 1, anchor: [0, 0] });
    steps.forEach(([, , cue], i) => {
      const t = s.rec.at(cue, 1) - 0.05;
      W.appear(ns[i], i ? W.edge(ns[i - 1], ns[i], { tone: steps[i][3] }) : null, t, { hold: 99 });
      if (i) ns[i - 1].lit(t + 0.1, 0.5, 0.5);
    });
  }, { exit: false, drift: 0 });
}
