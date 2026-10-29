// Reel 11 · Every drug has a clock. Source: Chapter 1, p 4 (Medication and allergies).
// A perioperative timeline: one row per drug, days relative to surgery on the x axis. The camera zooms to the window being discussed.
import { World, chip } from '../../engine/world.js';
import { h } from '../../engine/dom.js';
import { rich } from '../../engine/components.js';

import { script } from './script.js';
export { script };
// A scrolling chart: rows slide through the soft top/bottom fade by design.
export const audit = { fade: false };

const D0 = -12, D1 = 3, X0 = 96, X1 = 984;
const px = (d) => X0 + ((d - D0) / (D1 - D0)) * (X1 - X0);

export function build(R) {
  const s = R.s;
  const at = (id, w, n = 1) => s[id].at(w, n);

  R.scene(0, 60, (sc) => {
    document.head.append(h('style', {}, '.gn.tag { font-size: 34px; }'));
    const W = new World(R, sc, { size: [1080, 1900] });

    // ---------------------------------------------------------------- frame: title, day grid, surgery line
    const title = rich(R, 'Every drug has a *clock*', { cls: 'serif l', style: { position: 'absolute', left: '72px', top: '120px', width: '936px' } });
    W.el.append(title.el);

    const rows = [
      { id: 'ang', icon: 'heart-pulse', label: 'Antianginals', extra: 0 },
      { id: 'bb', icon: 'activity', label: 'β-blockers', extra: 0 },
      { id: 'ace', icon: 'pill', label: 'ACE inhibitors', extra: 1 },
      { id: 'asa', icon: 'droplet', label: 'Aspirin, clopidogrel', extra: 2 },
      { id: 'war', icon: 'tablets', label: 'Warfarin', extra: 1 },
      { id: 'ster', icon: 'flask-conical', label: 'Steroids', extra: 1 },
      { id: 'dm', icon: 'syringe', label: 'Long-acting hypoglycemics', extra: 1 },
    ];
    const TOP = 400, LINE = 78, EXTRA = 74, GAP = 52;
    let y = TOP;
    rows.forEach((r) => { r.y = y; y += LINE + 56 + r.extra * EXTRA + GAP; });
    const BOTTOM = y - GAP + 20;

    const grid = [];
    for (let d = D0; d <= D1; d++) {
      const major = d % 5 === 0 || d === 0;
      grid.push(h('div', { class: ['ggrid', major && 'major'], style: { left: `${px(d)}px`, top: `${TOP - 40}px`, height: `${BOTTOM - TOP + 40}px` } }));
    }
    const surg = h('div', { class: 'gsurg', style: { left: `${px(0)}px`, top: `${TOP - 150}px`, height: `${BOTTOM - TOP + 150}px` } });
    W.el.append(...grid, surg);
    const ticks = [[-10, '−10 d'], [-5, '−5 d'], [2, '+2 d']].flatMap(([d, t]) => [TOP - 96, BOTTOM + 30].map((yy) => h('div', { class: 'gtick', style: { left: `${px(d)}px`, top: `${yy}px` } }, t)));
    W.el.append(...ticks);
    const surgery = W.node('surgery', { kind: 'tag', icon: 'scissors', label: 'Surgery', tone: 'white', x: px(0), y: TOP - 122 });
    const surgery2 = W.node('surgery2', { kind: 'tag', icon: 'scissors', label: 'Surgery', tone: 'white', x: px(0), y: BOTTOM + 70 });
    const frame = [...grid, surg, ...ticks];
    frame.forEach((el) => R.chan(el, 'opacity').initial = 0);

    // ---------------------------------------------------------------- rows
    const segs = [];
    const seg = (row, kind, d0, d1, t0, t1, { alt = false } = {}) => {
      const el = h('div', { class: ['gseg', kind, alt && 'alt'], style: { left: `${px(d0)}px`, top: `${row.y + LINE + (alt ? 44 : 0)}px` } });
      W.el.append(el);
      R.chan(el, 'css:width', { initial: 0, unit: 'px' });
      R.tween(el, t0, Math.max(t1 - t0, 0.2), { 'css:width': px(d1) - px(d0) }, { ease: 'inOutSine' });
      el.dataset.kind = kind;
      segs.push({ el, kind, alt });
      return el;
    };
    const chip = (row) => {
      const n = W.node(row.id, { kind: 'chip', icon: row.icon, label: row.label, tone: 'white', cls: 'sm' });
      n.place(X0 - 6 + n.w / 2, row.y + 36);
      row.chip = n;
      return n;
    };
    const tag = (row, line, label, icon, tone, xRight) => {
      const n = W.node(`${row.id}_${label.slice(0, 6)}`, { kind: 'tag', icon, label, tone });
      const yy = row.y + 36 + (line ? LINE + 56 + (line - 1) * EXTRA - 12 + 10 : 0);
      n.place(xRight - n.w / 2, line ? row.y + LINE + 56 + (line - 1) * EXTRA + 30 : row.y + 36);
      return n;
    };
    rows.forEach(chip);

    const [ang, bb, ace, asa, war, ster, dm] = rows;
    // tags (right-aligned on the chip line or on extra lines); built left-to-right with measured widths
    const place = (row, line, specs) => {
      let xr = X1;
      return specs.slice().reverse().map(([label, icon, tone]) => { const n = tag(row, line, label, icon, tone, xr); xr -= n.w + 16; return n; }).reverse();
    };
    const T = {
      bb: place(bb, 0, [['back as BP and rhythm allow', 'trending-up', 'violet']]),
      ace0: place(ace, 0, [['24–48 h before', 'timer', 'pink']]),
      ace1: place(ace, 1, [['avoids profound dilatation', 'arrow-up-right', 'warn']]),
      asa0: place(asa, 0, [['5–10 days before', 'timer', 'pink']]),
      asa1: place(asa, 1, [['bleeding', 'droplet', 'warn'], ['ischemic risk rises', 'trending-up', 'warn']]),
      asa2: place(asa, 2, [['recent PCI', 'badge-alert', 'violet'], ['tight left main', 'badge-alert', 'violet'], ['may continue', 'circle-check', 'violet']]),
      war0: place(war, 0, [['5 days before', 'timer', 'pink']]),
      war1: place(war, 1, [['high risk: admit early for IV heparin', 'syringe', 'violet']]),
      st0: place(ster, 0, [['> 5 mg prednisone daily', 'pill', 'teal']]),
      st1: place(ster, 1, [['avoids an Addisonian crisis', 'triangle-alert', 'warn']]),
      dm1: place(dm, 1, [['morning of surgery', 'sunrise', 'pink'], ['sliding scale if needed', 'syringe', 'violet']]),
    };

    const zone = W.zone([...rows.map((r) => r.id), 'surgery', 'surgery2'], { tone: 'neutral', label: 'Days around surgery', pad: 56, extra: [{ x: X0, y: TOP - 150, w: X1 - X0, h: BOTTOM - TOP + 230 }] });

    // ---------------------------------------------------------------- choreography
    const appear = (n, t, hold = 99) => W.appear(n, null, t, { hold });
    const camTo = (t, x, yy, zoom, dur = 1.1) => W.cam(t, [x, yy], { zoom, dur, anchor: [540, 520] });
    const fitAll = (t, dur = 1.3) => W.cam(t, { x: 40, y: 100, w: 1000, h: BOTTOM + 330 - 100 }, { dur, fit: true, pad: 10 });

    // hook
    W.start([540, 330], { zoom: 0.95, anchor: [540, 470] });
    title.reveal([at('hook', 'every'), at('hook', 'drug'), at('hook', 'has'), at('hook', 'a'), at('hook', 'clock')].map((t, i) => (i < 4 ? t : t)), 0.0);
    title.words.forEach((w) => R.hide(w, at('cont', 'antianginals') - 0.45, { dur: 0.4, y: -30 }));
    zone.in(at('hook', 'drug') - 0.2);
    frame.forEach((el, i) => R.show(el, at('hook', 'drug') + (i % 7) * 0.03, { dur: 0.7, y: 0 }));
    appear(surgery, at('hook', 'clock') - 0.2);
    appear(surgery2, at('hook', 'clock') - 0.2);

    // continue until surgery
    W.cam(at('cont', 'antianginals') - 0.5, [540, ang.y + 150], { zoom: 1.04, dur: 1.2, anchor: [540, 560] });
    appear(ang.chip, at('cont', 'antianginals') - 0.1);
    appear(bb.chip, at('cont', 'β-blockers') - 0.1);
    seg(ang, 'on', D0, 0, at('cont', 'continue') - 0.05, at('cont', 'surgery') + 0.2);
    seg(bb, 'on', D0, 0, at('cont', 'continue') - 0.05, at('cont', 'surgery') + 0.2);
    // afterwards
    seg(ang, 'stop', 0, D1, at('after', 'stop') - 0.1, at('after', 'stop') + 0.6);
    seg(bb, 'decide', 0, D1, at('after', 'return') - 0.05, at('after', 'allow') + 0.3);
    appear(T.bb[0], at('after', 'pressure') - 0.2);

    // ACE inhibitors: 24–48 h
    W.cam(at('ace', 'ace') - 0.6, [540, ace.y + 120], { zoom: 1.04, dur: 1.2, anchor: [540, 560] });
    appear(ace.chip, at('ace', 'ace') - 0.1);
    seg(ace, 'on', D0, -2, at('ace', 'ace') - 0.05, at('ace', 'stop') + 0.3);
    seg(ace, 'fade', -2, -1, at('ace', 'stop') + 0.2, at('ace', 'before') + 0.1);
    seg(ace, 'stop', -1, 0, at('ace', 'before') + 0.1, at('ace', 'before') + 0.6);
    appear(T.ace0[0], at('ace', '24–48') - 0.1);
    appear(T.ace1[0], at('ace', 'avoid') - 0.1);

    // aspirin and clopidogrel: 5–10 days
    W.cam(at('asa', 'aspirin') - 0.6, [540, asa.y + 170], { zoom: 1.04, dur: 1.2, anchor: [540, 560] });
    appear(asa.chip, at('asa', 'aspirin') - 0.1);
    seg(asa, 'on', D0, -10, at('asa', 'aspirin') - 0.05, at('asa', 'stop') + 0.3);
    seg(asa, 'fade', -10, -5, at('asa', 'stop') + 0.3, at('asa', 'before') + 0.2);
    seg(asa, 'stop', -5, 0, at('asa', 'before') + 0.2, at('asa', 'bleeding') + 0.2);
    appear(T.asa0[0], at('asa', '5–10') - 0.1);
    appear(T.asa1[0], at('asa', 'bleeding') - 0.2);
    // but high-risk patients may continue
    appear(T.asa1[1], at('asa2', 'ischemic') - 0.1);
    seg(asa, 'decide', -5, 0, at('asa2', 'high-risk') - 0.05, at('asa2', 'continue') + 0.2, { alt: true });
    appear(T.asa2[0], at('asa2', 'recent') - 0.1);
    appear(T.asa2[1], at('asa2', 'tight') - 0.1);
    appear(T.asa2[2], at('asa2', 'continue') - 0.2);

    // warfarin
    W.cam(at('war', 'warfarin') - 0.6, [540, war.y + 130], { zoom: 1.04, dur: 1.2, anchor: [540, 560] });
    appear(war.chip, at('war', 'warfarin') - 0.1);
    seg(war, 'on', D0, -5, at('war', 'warfarin') - 0.05, at('war', 'stops') + 0.3);
    seg(war, 'stop', -5, 0, at('war', 'stops') + 0.3, at('war', 'before') + 0.4);
    appear(T.war0[0], at('war', 'five') - 0.1);
    appear(T.war1[0], at('war', 'thromboembolic') - 0.2);
    seg(war, 'decide', -2, 0, at('war', 'intravenous') - 0.1, at('war', 'heparin') + 0.3, { alt: true });

    // steroids
    W.cam(at('ster', 'steroids') - 0.6, [540, ster.y + 130], { zoom: 1.04, dur: 1.2, anchor: [540, 560] });
    appear(ster.chip, at('ster', 'steroids') - 0.1);
    seg(ster, 'on', D0, 0, at('ster', 'steroids') - 0.05, at('ster', 'daily') + 0.2);
    appear(T.st0[0], at('ster', 'above') - 0.1);
    seg(ster, 'decide', 0, 2, at('ster', 'give') - 0.05, at('ster', 'premedication') + 0.3);
    appear(T.st1[0], at('ster', 'avoid') - 0.1);

    // hypoglycemics
    W.cam(at('dm', 'long-acting') - 0.6, [540, dm.y + 130], { zoom: 1.04, dur: 1.2, anchor: [540, 560] });
    appear(dm.chip, at('dm', 'long-acting') - 0.1);
    seg(dm, 'on', D0, -0.4, at('dm', 'long-acting') - 0.05, at('dm', 'withheld') + 0.2);
    seg(dm, 'stop', -0.4, 0, at('dm', 'withheld') - 0.05, at('dm', 'morning') + 0.4);
    appear(T.dm1[0], at('dm', 'morning') - 0.1);
    seg(dm, 'decide', 0, D1, at('dm', 'insulin') - 0.05, at('dm', 'needed') + 0.3);
    appear(T.dm1[1], at('dm', 'sliding') - 0.1);

    // recap: continue / stop / decide light their bars
    const tRec = at('rec', 'continue');
    W.cam(tRec - 0.8, { x: 40, y: TOP - 170, w: 1000, h: BOTTOM - TOP + 190 }, { dur: 1.3, fit: true, pad: 6, anchor: [540, 430], max: 0.8 });
    Object.values(W.nodes).forEach((n) => R.tween(n.el, tRec - 0.6, 0.6, { opacity: 0.22 }, { ease: 'outCubic' }));
    segs.forEach(({ el }) => R.chan(el, 'css:--hl', { initial: 1 }));
    const light = (t, kinds) => segs.forEach(({ el, kind }) => R.tween(el, t, 0.4, { 'css:--hl': kinds.includes(kind) ? 1 : 0.0 }, { ease: 'outCubic' }));
    light(at('rec', 'continue') - 0.05, ['on', 'fade']);
    light(at('rec', 'stop') - 0.05, ['stop', 'fade']);
    light(at('rec', 'decide') - 0.05, ['decide']);
    light(at('rec', 'clock') - 0.1, ['on', 'fade', 'stop', 'decide']);
    W.finish();
  }, { drift: 0, exit: false });

  // ---------------------------------------------------------------- legend overlay (big, readable)
  R.scene(at('rec', 'continue') - 0.5, 60, (sc) => {
    const spec = [['circle-check', 'Continue', 'teal', 'continue'], ['circle-x', 'Stop', 'pink', 'stop'], ['circle-help', 'Decide', 'violet', 'decide']];
    const row = h('div', { class: 'flow', style: { left: '56px', top: '1268px', width: '968px', gap: '18px' } },
      ...spec.map(([icon, label, tone]) => chip(R, { icon, label, tone, size: 50 })));
    sc.add(row);
    [...row.children].forEach((el, i) => R.show(el, at('rec', spec[i][3]) - 0.1, { dur: 0.5, y: 24, scale: 0.9, ease: 'outSoft' }));
  }, { exit: false, drift: 0, enter: { y: 0 } });
}
