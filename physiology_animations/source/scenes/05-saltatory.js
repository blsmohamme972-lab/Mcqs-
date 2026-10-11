window.SCENE = {
  num: 5, system: 'Nervous system', color: '#d99a00',
  title: 'Saltatory conduction',
  layers: { n: '05_Nervous_and_Senses/Motor_neuron.svg' },
  steps: [
    { t0: 0.2, t1: 1.6, text: '<b>Dendrites</b> receive inputs; the soma sums EPSPs.' },
    { t0: 1.6, t1: 2.4, text: 'At the <b>axon hillock</b> threshold (≈ −55 mV) is reached → an <b>action potential</b> fires.' },
    { t0: 2.4, t1: 5.2, text: 'Myelin insulates the axon, so the impulse <b>jumps node to node</b> (Nodes of Ranvier) — up to ~120 m/s.' },
    { t0: 5.2, t1: 8.0, text: 'At the <b>neuromuscular junction</b> ACh is released → the muscle fibre contracts.' },
  ],
  widget: `<div class="wcard"><div class="wtitle">Membrane potential at the axon hillock</div><svg id="vm" viewBox="0 0 500 130" width="500" height="130"></svg></div>`,
  takeaway: { t: 6.0, text: 'Myelin + nodes = faster, energy-saving conduction. Demyelination (e.g. multiple sclerosis, Guillain–Barré) slows or blocks it.' },

  nodes: [[463, 348], [455, 409], [443, 468], [429, 527], [415, 585], [404, 644], [393, 702]],

  init(c) {
    const o = c.o;
    this.soma = c.el('circle', { cx: 468, cy: 200, r: 70, fill: '#fff59d', filter: 'url(#soft)', opacity: 0 }, o);
    // dendritic inputs travelling to the soma
    const tips = [[330, 185], [600, 190], [460, 60], [520, 80], [385, 255], [555, 245], [405, 120], [545, 130]];
    this.inputs = tips.map((p, i) => ({ k: i * .13, p: c.path([p, [(p[0] + 468) / 2 + (i % 2 ? 12 : -12), (p[1] + 200) / 2], [468, 200]], {}, o), e: c.el('circle', { r: 9, fill: '#ff8f00', stroke: '#fff', 'stroke-width': 3 }, o) }));
    this.hill = c.el('circle', { cx: 466, cy: 312, r: 26, fill: '#fff176', filter: 'url(#glow)', opacity: 0 }, o);
    this.ng = this.nodes.map(([x, y]) => c.el('circle', { cx: x, cy: y, r: 16, fill: '#ffeb3b', filter: 'url(#glow)', opacity: 0 }, o));
    // jump arcs between nodes
    this.arcs = [];
    for (let i = 0; i < this.nodes.length - 1; i++) {
      const [a, b] = [this.nodes[i], this.nodes[i + 1]];
      this.arcs.push(c.path([a, [(a[0] + b[0]) / 2 + 42, (a[1] + b[1]) / 2], b], { stroke: '#ff9800', 'stroke-width': 5, 'stroke-linecap': 'round', 'stroke-dasharray': '2 10', opacity: 0 }, o));
    }
    this.spark = c.el('circle', { r: 13, fill: '#fff', stroke: '#ff9800', 'stroke-width': 5, filter: 'url(#glow)', opacity: 0 }, o);
    const ends = [[265, 840], [345, 808], [365, 840], [405, 840], [455, 860], [485, 838], [285, 872]];
    this.term = ends.map(p => ({ p: c.path([[392, 708], [385, 738], [(385 + p[0]) / 2, (738 + p[1]) / 2 - 8], p], {}, o), e: c.el('circle', { r: 9, fill: '#ffeb3b', stroke: '#ff9800', 'stroke-width': 3 }, o) }));
    this.muscle = c.el('rect', { x: 222, y: 793, width: 280, height: 93, rx: 18, fill: '#ff1744', opacity: 0, filter: 'url(#soft)' }, o);
    this.ach = Array.from({ length: 14 }, (_, i) => c.el('circle', { r: 5, fill: '#00b8d4', opacity: 0 }, o));
    this.lSoma = c.label(690, 300, 'Soma', { lx: 520, ly: 230, color: '#8d6e00' });
    this.lHill = c.label(650, 345, 'Axon hillock', { lx: 470, ly: 318, color: '#b45309' });
    this.lMy = c.label(640, 480, 'Myelin sheath', { lx: 446, ly: 495, color: '#4f46e5' });
    this.lNode = c.label(210, 560, 'Node of Ranvier', { lx: 422, ly: 556, color: '#e65100' });
    this.lNmj = c.label(680, 770, 'Neuromuscular junction', { lx: 450, ly: 830, color: '#c62828' });

    // Vm trace
    const sv = document.getElementById('vm'); const E = (t, a) => c.el(t, a, sv);
    const X = t => 46 + t / 8 * 450, Y = v => 112 - (v + 85) * 0.85;
    this.X = X;
    E('line', { x1: 46, y1: Y(-55), x2: 496, y2: Y(-55), stroke: '#e57373', 'stroke-dasharray': '5 4' });
    const lab = (y, s, col) => { const t = E('text', { x: 40, y: y + 4, 'font-size': 11, 'text-anchor': 'end', fill: col || '#6b7896', 'font-family': 'Inter', 'font-weight': 600 }); t.textContent = s; };
    lab(Y(30), '+30'); lab(Y(-55), '−55', '#e57373'); lab(Y(-70), '−70');
    const thr = E('text', { x: 494, y: Y(-55) - 5, 'font-size': 11, 'text-anchor': 'end', fill: '#e57373', 'font-family': 'Inter', 'font-weight': 600 }); thr.textContent = 'threshold';
    const vm = t => {
      if (t < 1.75) { // EPSPs summating toward threshold
        let v = -70 + 15 * c.seg(t, .3, 1.75);
        v += 2.5 * Math.sin(t * 18) * c.seg(t, .3, .5);
        return v;
      }
      if (t < 2.0) return c.lerp(-55, 30, c.ease(c.seg(t, 1.75, 2.0)));
      if (t < 2.35) return c.lerp(30, -80, c.ease(c.seg(t, 2.0, 2.35)));
      return c.lerp(-80, -70, c.easeOut(c.seg(t, 2.35, 3.3)));
    };
    const pts = []; for (let t = 0; t <= 8.0001; t += .02) pts.push([X(t), Y(vm(t))]);
    this.trace = E('path', { d: 'M' + pts.map(p => p.join(',')).join('L'), fill: 'none', stroke: '#d99a00', 'stroke-width': 3.5, 'stroke-linejoin': 'round' });
    this.trace._len = this.trace.getTotalLength();
    this.apLab = E('text', { x: X(2.0) + 10, y: Y(30) + 10, 'font-size': 12, 'font-weight': 700, fill: '#d99a00', 'font-family': 'Inter' }); this.apLab.textContent = 'action potential';
    this.vm = vm;
    this.pen = E('circle', { r: 5, fill: '#d99a00' });
  },

  update(t, c) {
    const { set, seg, win } = c;
    set(this.soma, { opacity: .8 * seg(t, .3, 1.7) * (1 - seg(t, 2.2, 3.0)) });
    this.inputs.forEach(d => {
      const u = c.frac((t - .2) * .9 + d.k); const [x, y] = c.at(d.p, u);
      set(d.e, { cx: x, cy: y, opacity: win(t, .2, 1.9) * Math.min(1, u * 5, (1 - u) * 5) });
    });
    set(this.hill, { opacity: win(t, 1.7, 2.6, .2), r: 22 + 14 * seg(t, 1.7, 2.1) });
    // node timing
    const t0 = 2.4, dt = 0.4;
    this.ng.forEach((g, i) => { const a = t0 + i * dt; set(g, { opacity: Math.max(win(t, a - .05, a + .45, .12), .25 * seg(t, a, a + .1) * (1 - seg(t, 6.8, 7.4))) }); });
    this.arcs.forEach((p, i) => { const a = t0 + i * dt; p.style.opacity = win(t, a, a + .9, .2) * .9; });
    const k = (t - t0) / dt;
    if (k >= 0 && k < this.arcs.length) { const i = Math.floor(k); const [x, y] = c.at(this.arcs[i], c.ease(k - i)); set(this.spark, { cx: x, cy: y, opacity: 1 }); }
    else set(this.spark, { opacity: 0 });
    const tEnd = t0 + (this.nodes.length - 1) * dt; // 4.8
    this.term.forEach(d => { const u = seg(t, tEnd, tEnd + .5); const [x, y] = c.at(d.p, u); set(d.e, { cx: x, cy: y, opacity: win(t, tEnd, tEnd + 1.2, .15) }); });
    const m = seg(t, 5.3, 5.6) * (1 - seg(t, 7.2, 8));
    set(this.muscle, { opacity: .45 * m * (.6 + .4 * c.pulse(t - 5.3, .35)) });
    this.ach.forEach((a, i) => {
      const e = this.term[i % this.term.length].p; const [x, y] = c.at(e, 1);
      const u = c.frac((t - 5.2) * 1.2 + i / 14);
      set(a, { cx: x + (i % 3 - 1) * 10 * u, cy: y + 26 * u, opacity: win(t, 5.2, 7.6) * (1 - u) });
    });
    this.lSoma.setAttribute('opacity', win(t, .3, 2.4));
    this.lHill.setAttribute('opacity', win(t, 1.6, 3.4));
    this.lMy.setAttribute('opacity', seg(t, 2.5, 2.8));
    this.lNode.setAttribute('opacity', seg(t, 2.9, 3.2));
    this.lNmj.setAttribute('opacity', seg(t, 5.0, 5.3));
    c.reveal(this.trace, t / 8);
    set(this.pen, { cx: this.X(t), cy: 112 - (this.vm(t) + 85) * .85 });
    this.apLab.setAttribute('opacity', seg(t, 2.0, 2.3));
  },
};
