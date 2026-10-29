// Reel 16 · The short examination as a route over the body. Source: Chapter 1, p 6 (Examination, Box 1.2).
// Eight numbered stations appear on the hologram body as the narrator reaches them; the list on the right is an accordion
// (only the current step shows its details), and the camera follows the body region being examined.
import { World } from '../../engine/world.js';
import { body, LM, hotspot } from '../../engine/body.js';
import { drawPath } from '../../engine/components.js';
import { h } from '../../engine/dom.js';

import { script } from './script.js';
export { script };

export function build(R) {
  const s = R.s;
  const at = (id, w, n = 1) => s[id].at(w, n);

  R.scene(0, 60, (sc) => {
    document.head.append(h('style', {}, `
      .mk { position: absolute; display: grid; place-items: center; width: 52px; height: 52px; border-radius: 50%; font: 700 32px/1 var(--mono); color: #0b0b12; background: var(--teal); box-shadow: 0 0 0 5px var(--ink), 0 0 26px color-mix(in srgb, var(--teal) 70%, transparent); }
      .scan { position: absolute; height: 5px; border-radius: 3px; background: linear-gradient(90deg, transparent, var(--teal-t), transparent); box-shadow: 0 0 28px 6px color-mix(in srgb, var(--teal) 60%, transparent); }
      .gn.tag { font-size: 34px; }
    `));
    const W = new World(R, sc, { size: [1080, 1750] });
    const BX = 54, BY = 380, BS = 0.8;
    const B = body(R, { x: BX, y: BY, scale: BS, id: 'bd16' });
    W.el.append(B.svg);
    R.chan(B.svg, 'opacity').initial = 0;
    const P = (bx, by) => B.pt([bx, by]);
    const C = LM.head[0]; // body axis

    // ---------------------------------------------------------------- title
    const title = W.node('title', { kind: 'start', icon: 'stethoscope', label: 'Short examination', tone: 'teal', x: 540, y: 230 });

    // ---------------------------------------------------------------- purposes and "short"
    const colX = 552;
    const purposes = [
      { id: 'p1', icon: 'search', label: 'Find disease', cue: ['purpose', 'find'] },
      { id: 'p2', icon: 'map', label: 'Plan the surgery', cue: ['purpose', 'help'] },
      { id: 'p3', icon: 'timer', label: 'Spot delays', cue: ['purpose', 'spot'] },
    ].map((sp, i) => { const n = W.node(sp.id, { kind: 'chip', icon: sp.icon, label: sp.label, tone: 'pink', cls: 'sm' }); n.place(colX + n.w / 2, 570 + i * 104); n.cue = sp.cue; return n; });
    const shortTag = W.node('short', { kind: 'tag', icon: 'zap', label: 'Short version is enough', tone: 'violet', x: 0, y: 0 });
    shortTag.place(colX + shortTag.w / 2, 570 + 3 * 104 + 20);

    // ---------------------------------------------------------------- the eight steps
    const steps = [
      { icon: 'activity', label: 'Pulse: rate, rhythm', cue: ['st1', 'pulse'], at: P(C - 236, 702), tag: [] },
      { icon: 'gauge', label: 'Blood pressure', cue: ['st1', 'blood'], at: P(C - 200, 470), tag: [] },
      { icon: 'droplets', label: 'JVP', cue: ['st2', 'jugular'], at: P(C - 24, 226), tag: [['jugular venous pressure', 'st2', 'venous'], ['patient at 45°', 'st2', '45°']] },
      { icon: 'stethoscope', label: 'Auscultate', cue: ['st3', 'auscultate'], at: P(C + 30, 410), tag: [['heart sounds', 'st3', 'heart'], ['carotids', 'st3', 'carotids'], ['breath sounds', 'st3', 'breath'], ['scars', 'st3', 'scars']] },
      { icon: 'hand', label: 'Abdomen', cue: ['st4', 'abdomen'], at: P(C, 640), tag: [['tenderness', 'st4', 'tenderness'], ['hernias', 'st4', 'hernias'], ['organomegaly', 'st4', 'organomegaly'], ['scars', 'st4', 'scars']] },
      { icon: 'footprints', label: 'Peripheral pulses', cue: ['st5', 'peripheral'], at: P(C - 62, 792), tag: [['incl. abdominal aorta', 'st5', 'including']] },
      { icon: 'waves', label: 'Pedal edema', cue: ['st6', 'pedal'], at: P(C - 86, 1036), tag: [] },
      { icon: 'git-branch', label: 'Conduits', cue: ['st6', 'conduits'], at: P(C + 66, 930), tag: [['may become grafts', 'st6', 'may']] },
    ];
    const Y0 = 500, PITCH = 100;
    steps.forEach((st, i) => {
      st.chip = W.node(`s${i + 1}`, { kind: 'chip', icon: st.icon, label: st.label, tone: 'teal', num: i + 1, cls: 'sm' });
      st.chip.place(colX + st.chip.w / 2, Y0 + i * PITCH);
      // detail tags wrap into rows under the chip
      let tx = colX + 18, ty = Y0 + i * PITCH + 66;
      st.tags = st.tag.map(([label]) => {
        const n = W.node(`s${i + 1}t${label.slice(0, 5)}`, { kind: 'tag', label, tone: 'teal' });
        if (tx + n.w > 1030) { tx = colX + 18; ty += 64; }
        n.place(tx + n.w / 2, ty);
        tx += n.w + 14;
        return n;
      });
      st.badge = h('div', { class: 'mk' }, String(i + 1));
      W.el.append(st.badge);
      st.badge.style.left = `${st.at[0] - 26}px`;
      st.badge.style.top = `${st.at[1] - 26}px`;
      R.chan(st.badge, 'opacity').initial = 0;
    });

    // route: thin line from each station to the next
    const route = steps.slice(1).map((st, i) => {
      const a = steps[i].at, b = st.at;
      const path = h('path', { d: `M${a[0]} ${a[1]} Q${(a[0] + b[0]) / 2 + (i % 2 ? 40 : -40)} ${(a[1] + b[1]) / 2} ${b[0]} ${b[1]}`, fill: 'none', stroke: 'var(--teal-t)', 'stroke-width': 3, 'stroke-linecap': 'round', opacity: 0.4 });
      W.svg.append(path);
      return path;
    });

    // ---------------------------------------------------------------- choreography
    const appear = (n, t, hold = 99) => W.appear(n, null, t, { hold });
    const cam = (t, y, zoom = 1.0, dur = 1.1) => W.cam(t, [540, y], { zoom, dur, anchor: [540, 540] });

    W.start([540, 590], { zoom: 1.0, anchor: [540, 520] });
    // hook: scan the body
    appear(title, at('hook', 'eight') - 0.2);
    R.show(B.svg, at('hook', 'steps') - 0.1, { dur: 1.0, y: 0 });
    const scan = h('div', { class: 'scan', style: { left: `${BX - 30}px`, width: `${560 * BS + 60}px` } });
    W.el.append(scan);
    R.chan(scan, 'opacity').initial = 0;
    R.tween(scan, at('hook', 'steps'), 0.3, { opacity: 1 });
    R.fn(at('hook', 'steps'), at('hook', 'examination') + 0.7, (p) => { scan.style.top = `${BY + 20 + p * (1080 * BS - 20)}px`; }, { ease: 'inOutSine' });
    R.tween(scan, at('hook', 'examination') + 0.5, 0.4, { opacity: 0 });

    // purposes and "short"
    cam(at('purpose', 'its') - 0.4, 830, 1.0, 1.4);
    purposes.forEach((n) => { appear(n, at(...n.cue) - 0.1, 99); R.hide(n.el, at('short', 'sufficient') + 0.6, { dur: 0.45, y: 0 }); });
    appear(shortTag, at('short', 'average') - 0.15, 99);
    R.hide(shortTag.el, at('short', 'sufficient') + 0.6, { dur: 0.45, y: 0 });

    // steps
    const camY = [820, 820, 790, 830, 860, 870, 860, 860];
    steps.forEach((st, i) => {
      const t = at(...st.cue) - 0.1;
      if (i === 2 || i === 3 || i === 4 || i === 5 || i === 6) cam(t - 0.5, camY[i], 1.0, 1.3);
      appear(st.chip, t, 99);
      R.show(st.badge, t + 0.1, { dur: 0.5, y: 0, scale: 0.4, ease: 'outSoft' });
      hotspot(R, W.el, st.at, { t0: t + 0.1, tone: 'teal', size: 30, core: 0 });
      if (i) drawPath(R, route[i - 1], t, 0.7, { ease: 'inOutCubic' });
      // details only while the step is current
      st.tags.forEach((tg, k) => { appear(tg, at(...st.tag[k].slice(1)) - 0.1, 99); });
      const next = steps[i + 1] ? at(...steps[i + 1].cue) - 0.1 : at('st6', 'grafts') + 1.5;
      st.tags.forEach((tg) => R.hide(tg.el, next - 0.5, { dur: 0.4, y: 0 }));
      st.chip.lit(next, 0.45, 0.5);
    });

    // body sites for the multi-part steps
    const ring = (t, p, tone = 'teal', size = 24) => hotspot(R, W.el, p, { t0: t, tone, size, core: 9 });
    ring(at('st3', 'carotids') - 0.05, P(C + 24, 224));
    ring(at('st3', 'breath') - 0.05, P(C - 76, 372));
    ring(at('st3', 'breath') + 0.15, P(C + 86, 372));
    ring(at('st4', 'tenderness') - 0.05, P(C - 56, 610), 'teal', 20);
    ring(at('st4', 'hernias') - 0.05, P(C + 56, 700), 'teal', 20);
    ring(at('st4', 'organomegaly') - 0.05, P(C + 58, 600), 'teal', 20);
    ring(at('st5', 'including') + 0.1, P(C, 590));
    ring(at('st5', 'peripheral') + 0.2, P(C + 62, 792));
    ring(at('st5', 'pulses') - 0.05, P(C - 84, 1060));
    ring(at('st5', 'pulses') + 0.15, P(C + 84, 1060));
    ring(at('st6', 'pedal') + 0.2, P(C + 86, 1036), 'teal', 28);
    // scar mark on the sternum, leg veins as conduits
    const scar = h('path', { d: `M${P(C, 300)[0]} ${P(C, 300)[1]} L${P(C, 470)[0]} ${P(C, 470)[1]}`, fill: 'none', stroke: 'var(--warn)', 'stroke-width': 5, 'stroke-dasharray': '10 9', 'stroke-linecap': 'round' });
    W.svg.append(scar);
    R.chan(scar, 'opacity').initial = 0;
    R.tween(scar, at('st3', 'scars') - 0.05, 0.4, { opacity: 0.9 });
    R.tween(scar, at('st4', 'abdomen') - 0.2, 0.4, { opacity: 0 });
    const veins = [1, -1].map((sg) => {
      const pts = [[C + sg * 58, 830], [C + sg * 64, 900], [C + sg * 70, 970], [C + sg * 74, 1032]].map(([x, y]) => P(x, y));
      const v = h('path', { d: `M${pts.map((p) => p.join(' ')).join(' L')}`, fill: 'none', stroke: 'var(--violet-t)', 'stroke-width': 7, 'stroke-linecap': 'round', style: { filter: 'drop-shadow(0 0 8px var(--violet))' } });
      W.svg.append(v);
      drawPath(R, v, at('st6', 'conduits') - 0.05, 1.1, { ease: 'inOutCubic' });
      return v;
    });

    // recap: each station lights as its word is spoken
    cam(at('rec', 'pulse') - 0.6, 830, 0.98, 1.2);
    steps.forEach((st, i) => {
      const t = at('rec', ['pulse', 'pressure', 'veins', 'chest', 'abdomen', 'pulses', 'edema', 'conduits'][i]);
      st.chip.lit(t - 0.05, 1, 0.3).pop(t - 0.05);
      st.chip.lit(t + 0.7, 0.55, 0.5);
      R.tween(st.badge, t - 0.05, 0.2, { scale: 1.35 }, { ease: 'outCubic' });
      R.tween(st.badge, t + 0.25, 0.4, { scale: 1 }, { ease: 'outSoft' });
    });
  }, { drift: 0, exit: false });
}
