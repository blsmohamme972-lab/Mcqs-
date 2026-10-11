window.SCENE = {
  num: 9, system: 'Cardiovascular', color: '#0e8a9a',
  title: 'Starling forces in a capillary',
  layers: { cap: '01_Cardiovascular/capillary.svg' },
  steps: [
    { t0: 0.2, t1: 1.6, text: 'Two forces act across the wall: <b>hydrostatic pressure</b> pushes fluid out, <b>oncotic pressure</b> (albumin) pulls it in.' },
    { t0: 1.6, t1: 3.8, text: '<b>Arterial end:</b> hydrostatic 35 > oncotic 25 → net <b>filtration</b> out.' },
    { t0: 3.8, t1: 6.0, text: '<b>Venous end:</b> hydrostatic 15 < oncotic 25 → net <b>reabsorption</b> in.' },
    { t0: 6.0, t1: 8.0, text: 'The small excess left in the tissue is returned by <b>lymphatics</b>.' },
  ],
  widget: `<div class="wcard" style="display:flex;gap:12px">
    <div id="wa" style="flex:1;padding:8px 10px;border-radius:10px;background:#f1f5fa"><div class="wtitle">Arterial end</div><div style="font:600 14px/1.5 Inter">P<sub>c</sub> 35 out · π<sub>c</sub> 25 in<br><span style="color:#0e8a9a">Net +10 → out</span></div></div>
    <div id="wv" style="flex:1;padding:8px 10px;border-radius:10px;background:#f1f5fa"><div class="wtitle">Venous end</div><div style="font:600 14px/1.5 Inter">P<sub>c</sub> 15 out · π<sub>c</sub> 25 in<br><span style="color:#c2417a">Net −10 → in</span></div></div></div>`,
  takeaway: { t: 6.6, text: 'Oedema = ↑ capillary hydrostatic pressure (heart failure), ↓ albumin (liver disease, nephrotic syndrome), ↑ permeability, or blocked lymph.' },

  init(c) {
    const o = c.o;
    this.flow = c.path([[880, 605], [700, 575], [500, 535], [300, 480], [130, 440]], {}, o);
    this.rbc = Array.from({ length: 8 }, (_, i) => c.el('ellipse', { rx: 22, ry: 12, fill: '#d63a3a', stroke: '#fff', 'stroke-width': 3 }, o));
    const arr = (col) => ({ stroke: col, 'stroke-width': 10, 'marker-end': 'url(#ah)', 'stroke-linecap': 'round' });
    this.outA = c.el('g', { opacity: 0 }, o);
    for (const x of [640, 760]) {
      const yt = x == 640 ? 505 : 518, yb = x == 640 ? 670 : 690;
      c.el('line', Object.assign({ x1: x, y1: yt + 40, x2: x - 8, y2: yt - 70 }, arr('#0e8a9a')), this.outA);
      c.el('line', Object.assign({ x1: x, y1: yb - 40, x2: x + 8, y2: yb + 70 }, arr('#0e8a9a')), this.outA);
    }
    this.inV = c.el('g', { opacity: 0 }, o);
    for (const x of [260, 360]) {
      const yt = x == 260 ? 380 : 420, yb = x == 260 ? 575 : 615;
      c.el('line', Object.assign({ x1: x - 8, y1: yt - 80, x2: x, y2: yt + 35 }, arr('#c2417a')), this.inV);
      c.el('line', Object.assign({ x1: x + 8, y1: yb + 80, x2: x, y2: yb - 35 }, arr('#c2417a')), this.inV);
    }
    // fluid droplets
    const mk = (n, col) => Array.from({ length: n }, () => c.el('circle', { r: 8, fill: col, stroke: '#fff', 'stroke-width': 2.5 }, o));
    this.fOut = mk(8, '#29b6f6'); this.fIn = mk(8, '#29b6f6');
    this.lym = mk(5, '#7cb342');
    this.lA = c.label(720, 380, 'Arterial end', { color: '#0e8a9a' });
    this.lV = c.label(250, 220, 'Venous end', { color: '#c2417a' });
    this.lF = c.label(760, 800, 'Filtration', { color: '#0e8a9a', size: 23 });
    this.lR = c.label(240, 720, 'Reabsorption', { color: '#c2417a', size: 23 });
    this.lL = c.label(520, 830, 'Lymphatic drainage', { color: '#558b2f', size: 23 });
    this.lFlow = c.label(500, 470, '← blood flow', { color: '#1f2a44', size: 21 });
    this.lFlow.setAttribute('transform', 'rotate(14 500 470)');
  },

  update(t, c) {
    const { set, seg, win } = c;
    this.rbc.forEach((e, i) => { const u = c.frac(t * .16 + i / 8); const [x, y] = c.at(this.flow, u); set(e, { cx: x, cy: y + 14 * Math.sin(i * 2.3), transform: `rotate(14 ${x} ${y})`, opacity: Math.min(1, u * 8, (1 - u) * 8) }); });
    const A = win(t, 1.6, 8.2, .4), V = win(t, 3.8, 8.2, .4);
    this.outA.setAttribute('opacity', A * .9); this.inV.setAttribute('opacity', V * .9);
    this.fOut.forEach((d, i) => {
      const u = c.frac((t - 1.6) * .8 + i / 8 * 2); const x = [640, 760][i % 2], top = i % 4 < 2;
      const y0 = top ? (x == 640 ? 540 : 555) : (x == 640 ? 635 : 650), y1 = top ? y0 - 130 : y0 + 130;
      set(d, { cx: x + (top ? -8 : 8) * u, cy: c.lerp(y0, y1, u), opacity: A * Math.min(1, u * 5, (1 - u) * 5) });
    });
    this.fIn.forEach((d, i) => {
      const u = c.frac((t - 3.8) * .8 + i / 8 * 2); const x = [260, 360][i % 2], top = i % 4 < 2;
      const y1 = top ? (x == 260 ? 415 : 455) : (x == 260 ? 540 : 580), y0 = top ? y1 - 130 : y1 + 130;
      set(d, { cx: x, cy: c.lerp(y0, y1, u), opacity: V * Math.min(1, u * 5, (1 - u) * 5) });
    });
    this.lym.forEach((d, i) => {
      const u = c.frac((t - 6.0) * .5 + i / 5);
      set(d, { cx: c.lerp(700, 560, u) + 10 * Math.sin(i * 3), cy: c.lerp(770, 860, u), opacity: win(t, 6.0, 8.2, .3) * Math.min(1, u * 5, (1 - u) * 5) });
    });
    this.lA.setAttribute('opacity', seg(t, 1.6, 1.9));
    this.lV.setAttribute('opacity', seg(t, 3.8, 4.1));
    this.lF.setAttribute('opacity', seg(t, 2.0, 2.3));
    this.lR.setAttribute('opacity', seg(t, 4.2, 4.5));
    this.lL.setAttribute('opacity', seg(t, 6.0, 6.3));
    this.lFlow.setAttribute('opacity', win(t, .3, 2.6));
    document.getElementById('wa').style.background = t >= 1.6 && t < 3.8 ? '#dff3f5' : '#f1f5fa';
    document.getElementById('wv').style.background = t >= 3.8 && t < 6.0 ? '#fbe4ef' : '#f1f5fa';
  },
};
