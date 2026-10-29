// Reel 01 · The assessment map. Source: Chapter 1 opener (p 1) and the aims on pp 2, 4 and 6.
import { h } from '../../engine/dom.js';
import { rich } from '../../engine/components.js';

import { script } from './script.js';
export { script };

const STATIONS = [
  { ic: 'heart-pulse', lb: 'Cardiovascular history', pg: 'p 2', tone: 'var(--pink)', main: true, cue: 'cardiovascular', s: 'bed' },
  { ic: 'clipboard-list', lb: 'Systems enquiry', pg: 'p 4', tone: 'var(--teal)', main: true, cue: 'systems', s: 'bed' },
  { ic: 'stethoscope', lb: 'Examination', pg: 'p 6', tone: 'var(--violet)', main: true, cue: 'examination', s: 'bed' },
  { ic: 'flask-conical', lb: 'Routine laboratory tests', pg: 'p 8', cue: 'blood', s: 'inv' },
  { ic: 'scan-line', lb: 'Plain chest radiograph', pg: 'p 12', cue: 'chest', s: 'inv' },
  { ic: 'layers', lb: 'Computed tomography', pg: 'p 16', cue: 'CT', s: 'inv' },
  { ic: 'spline', lb: 'Cardiac catheterization', pg: 'p 18', cue: 'catheterization', s: 'inv' },
  { ic: 'git-branch', lb: 'Interpreting coronary imaging', pg: 'p 20', cue: 'coronary', s: 'inv' },
  { ic: 'gauge', lb: 'Cardiac hemodynamics', pg: 'p 22', cue: 'hemodynamics', s: 'inv' },
  { ic: 'audio-waveform', lb: 'Echocardiography', pg: 'p 24', cue: ['echo', 1], s: 'inv' },
  { ic: 'scan-eye', lb: 'Echo interpretation', pg: 'p 26', cue: 'echo interpretation', s: 'inv' },
  { ic: 'droplets', lb: 'Perfusion and viability', pg: 'p 28', cue: 'perfusion', s: 'inv' },
  { ic: 'clipboard-check', lb: 'General pre-op checklist', pg: 'p 30', cue: 'checklist', s: 'chk' },
];

const TOOLS = { History: ['heart-pulse', 'pink'], Systems: ['clipboard-list', 'teal'], Examination: ['stethoscope', 'violet'] };
const AIMS = [
  { n: '1', name: 'Indication', s: 'a1', lines: [
    ['History', 'Establish the indications for surgery', 'indicated'],
    ['Systems', 'Contraindications to elective surgery', 'contraindicated'],
    ['Examination', 'Disease needing further investigation', 'disease'],
  ] },
  { n: '2', name: 'Plan', s: 'a2', lines: [
    ['History', 'Issues outside standard protocols'],
    ['Systems', 'Problems altering standard management'],
    ['Examination', 'Help plan the surgery'],
  ] },
  { n: '3', name: 'Risk & recovery', s: 'a3', lines: [
    ['History', 'Estimate risk: mortality, stroke'],
    ['Systems', 'Problems that could delay discharge'],
    ['Examination', 'Problems that may delay recovery'],
  ] },
];

export function build(R) {
  const { s } = R;
  const at = (st) => R.s[st.s].at(...[].concat(st.cue));

  // ---------------------------------------------------------------- A · hook
  R.scene(0, s.bed.start + 0.15, (sc) => {
    const l1 = rich(R, 'Before the first incision,', { cls: 'serif l t2', style: { left: '72px', top: '330px', position: 'absolute', width: '936px' } });
    const num = h('div', { class: 'abs serif hero grad', style: { left: '70px', top: '480px' } }, '13');
    const l2 = rich(R, 'topics decide', { cls: 'serif l', style: { left: '72px', top: '980px', position: 'absolute', width: '936px' } });
    const l3 = rich(R, 'whether *and how* we operate.', { cls: 'serif l', style: { left: '72px', top: '1100px', position: 'absolute', width: '936px' } });
    sc.add(l1.el, num, l2.el, l3.el);
    l1.reveal(0.15, 0.1);
    R.show(num, s.hook.at('thirteen') - 0.05, { dur: 1.1, y: 60, scale: 0.9, blur: 18, ease: 'outExpo' });
    l2.reveal([s.hook.at('topics'), s.hook.at('decide')]);
    l3.reveal([s.hook.at('whether'), s.hook.at('and'), s.hook.at('how'), s.hook.at('we'), s.hook.at('operate')]);
  }, { exit: { y: -40 } });

  // ---------------------------------------------------------------- B · the map
  const PITCH = 74;
  const groupY = [232, 518, 1248];
  const stY = STATIONS.map((_, i) => (i < 3 ? 276 + i * PITCH : i < 12 ? 562 + (i - 3) * PITCH : 1292));
  R.scene(s.bed.start - 0.2, s.aims.start - 0.1, (sc) => {
    const top = stY[0] + 33, bottom = stY[12] + 33;
    const base = h('div', { class: 'rail', style: { top: `${top}px`, height: `${bottom - top}px`, background: 'rgba(255,255,255,.08)' } });
    const prog = h('div', { class: 'rail', style: { top: `${top}px`, height: '0px', background: `linear-gradient(180deg, var(--pink) 0px, var(--teal) ${PITCH}px, var(--violet) ${2 * PITCH}px, rgba(255,255,255,.75) ${3 * PITCH + 60}px)` } });
    R.chan(prog, 'css:height', { initial: 0, unit: 'px' });
    sc.add(base, prog);

    [['3', 'At the bedside', 0], ['9', 'Investigations', 3], ['1', 'Check', 12]].forEach(([n, txt, first], gi) => {
      const g = h('div', { class: 'grp', style: { top: `${groupY[gi]}px` } }, h('b', {}, n), txt);
      sc.add(g);
      R.show(g, at(STATIONS[first]) - 0.25, { dur: 0.6, y: 16 });
    });

    const lights = [];
    STATIONS.forEach((st, i) => {
      const el = h('div', { class: ['stn', st.main && 'main'], style: { top: `${stY[i]}px`, '--tone': st.tone ?? 'var(--t1)' } },
        h('i', { class: 'node' }), R.icon(st.ic, { size: 46, stroke: 1.7 }), h('div', { class: 'lb' }, st.lb), h('div', { class: 'pg' }, st.pg));
      el.querySelector('.icon').classList.add('ic');
      R.chan(el, 'css:--lit', { initial: 0 });
      sc.add(el);
      const t = at(st);
      R.show(el, t - 0.05, { dur: 0.55, y: 26 });
      R.tween(el, t - 0.05, 0.35, { 'css:--lit': 1 }, { ease: 'outCubic' });
      if (i > 0) R.tween(lights[i - 1], t - 0.05, 0.5, { 'css:--lit': 0.42 }, { ease: 'outCubic' });
      R.tween(prog, t - 0.05, 0.55, { 'css:height': stY[i] + 33 - top }, { ease: 'outCubic' });
      lights.push(el);
    });
    R.tween(lights.at(-1), s.chk.end + 0.2, 0.6, { 'css:--lit': 0.6 }, { ease: 'outCubic' });
  });

  // ---------------------------------------------------------------- C · three tools, three aims
  const panelY = [236, 600, 964];
  R.scene(s.aims.start - 0.1, s.rec.start - 0.1, (sc) => {
    const panels = AIMS.map((a, pi) => {
      const el = h('div', { class: 'panel apanel', style: { top: `${panelY[pi]}px` } });
      const num = h('b', {}, a.n), name = h('span', {}, a.name);
      el.append(h('div', { class: 'ph' }, num, name));
      const lines = a.lines.map(([who, text], li) => {
        const [ic, tone] = TOOLS[who];
        const icon = R.icon(ic, { size: 46, stroke: 1.7 });
        icon.classList.add('ic');
        const ln = h('div', { class: 'aim', style: { top: `${118 + li * 72}px`, '--tone': `var(--${tone})` } }, icon, h('div', { class: 'tx' }, text));
        R.chan(ln, 'css:--hl', { initial: 0 });
        el.append(ln);
        return ln;
      });
      sc.add(el);
      return { el, num, name, lines, a };
    });
    // "three aims": three empty numbered panels
    const tThree = s.aims.at('three');
    panels.forEach((p, i) => {
      R.show(p.el, tThree - 0.1 + i * 0.16, { dur: 0.7, y: 50 });
      R.show(p.num, tThree + i * 0.16, { dur: 0.6, y: 20, scale: 0.8 });
      R.chan(p.name, 'opacity').initial = 0;
    });
    panels.forEach(({ el, name, lines, a }, pi) => {
      const S = R.s[a.s];
      R.show(name, S.start, { dur: 0.6, y: 14 });
      lines.forEach((ln, li) => {
        const cue = a.lines[li][2];
        const t = cue ? S.at(cue) : S.frac([0.08, 0.42, 0.76][li]);
        R.show(ln, t - 0.05, { dur: 0.65, y: 30, x: 24 });
      });
      if (pi < 2) R.tween(el, R.s[AIMS[pi + 1].s].start, 0.5, { opacity: 0.4 }, { ease: 'outCubic' });
    });
    // "close": each tool lights its row in all three panels
    ['history', 'systems', 'examination'].forEach((c, ti) => {
      const t = s.close.at(c);
      panels.forEach(({ el, lines }) => {
        R.tween(el, s.close.start, 0.4, { opacity: 1 }, { ease: 'outCubic' });
        R.tween(lines[ti], t - 0.05, 0.3, { 'css:--hl': 1 }, { ease: 'outCubic' });
        R.tween(lines[ti], t + 1.5, 0.4, { 'css:--hl': 0 }, { ease: 'outCubic' });
      });
    });
  });

  // ---------------------------------------------------------------- D · recap
  R.scene(s.rec.start - 0.15, 60, (sc) => {
    const words = [['Indication.', 'indication', 'Why operate, or not?', 270], ['Plan.', 'plan', 'What must change?', 640], ['Risk.', 'risk', 'What could go wrong?', 1010]];
    words.forEach(([w, cue, sub, y], i) => {
      const t = s.rec.at(cue) - 0.05;
      const num = h('div', { class: 'abs micro', style: { left: '72px', top: `${y}px` } }, `0${i + 1}`);
      const el = h('div', { class: 'abs serif hero2 grad', style: { left: '72px', top: `${y + 56}px` } }, w);
      const sb = h('div', { class: 'abs body', style: { left: '76px', top: `${y + 262}px` } }, sub);
      sc.add(num, el, sb);
      R.show(num, t, { dur: 0.5, y: 12 });
      R.show(el, t, { dur: 0.9, y: 50, blur: 14, ease: 'outExpo' });
      R.show(sb, t + 0.25, { dur: 0.6, y: 18 });
    });
  }, { exit: false, drift: 0 });
}
