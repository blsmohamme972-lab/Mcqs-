window.SCENE = {
  num: 3, system: 'Respiratory', color: '#c2417a',
  title: 'Why air flows into the lungs',
  layers: { exp: '02_Respiratory/breathing-expiration.svg', ins: '02_Respiratory/breathing-inspiration.svg' },
  steps: [
    { t0: 0.6, t1: 2.4, text: '<b>Inspiration:</b> diaphragm contracts and flattens; external intercostals lift the ribs.' },
    { t0: 2.4, t1: 4.4, text: 'Thoracic volume ↑ → alveolar pressure falls <b>below atmospheric</b> → air flows <b>in</b>.' },
    { t0: 4.4, t1: 6.0, text: '<b>Quiet expiration is passive:</b> diaphragm relaxes, lungs recoil elastically.' },
    { t0: 6.0, t1: 8.0, text: 'Volume ↓ → alveolar pressure rises <b>above atmospheric</b> → air flows <b>out</b>.' },
  ],
  widget: `<div class="wcard"><div class="wtitle">Lung volume &amp; alveolar pressure</div><svg id="trace" viewBox="0 0 500 150" width="500" height="150"></svg></div>`,
  takeaway: { t: 6.6, text: "Boyle's law: P × V = constant. Air always moves from high to low pressure — muscles change volume, volume changes pressure." },

  // breathing state 0 = rest/expired, 1 = full inspiration
  s(t) { return t < 4.4 ? this.c.ease(this.c.seg(t, 0.8, 3.6)) : 1 - this.c.ease(this.c.seg(t, 4.5, 7.4)); },

  init(c) {
    this.c = c;
    const o = c.o;
    const arr = { stroke: '#0b6aa2', 'stroke-width': 9, 'marker-end': 'url(#ah)', 'stroke-linecap': 'round' };
    this.ribs = c.el('g', {}, o);
    c.el('line', Object.assign({ x1: 150, y1: 420, x2: 70, y2: 380 }, arr), this.ribs);
    c.el('line', Object.assign({ x1: 750, y1: 420, x2: 830, y2: 380 }, arr), this.ribs);
    this.lDia = c.label(450, 600, 'Diaphragm contracts ↓', { color: '#7a2f8f' });
    this.lDia2 = c.label(450, 600, 'Diaphragm relaxes ↑', { color: '#7a2f8f' });
    this.lRib = c.label(110, 330, 'Ribs up & out', { color: '#0b6aa2', size: 22 });
    // air particles streaming down/up the midline above the sternum
    this.air = Array.from({ length: 8 }, () => c.el('circle', { r: 9, fill: '#5cc8ef', stroke: '#fff', 'stroke-width': 3 }, o));
    this.lAir = c.label(450, 40, 'AIR IN', { color: '#0b6aa2', size: 22 });
    this.lAir2 = c.label(450, 40, 'AIR OUT', { color: '#0b6aa2', size: 22 });

    // widget traces
    const sv = document.getElementById('trace');
    const E = (tag, a, p = sv) => c.el(tag, a, p);
    E('line', { x1: 40, y1: 110, x2: 495, y2: 110, stroke: '#c9d2e0', 'stroke-dasharray': '4 4' });
    const tv = E('text', { x: 0, y: 44, 'font-size': 12, fill: '#c2417a', 'font-weight': 700, 'font-family': 'Inter' }); tv.textContent = 'Volume';
    const tp = E('text', { x: 0, y: 106, 'font-size': 12, fill: '#0b6aa2', 'font-weight': 700, 'font-family': 'Inter' }); tp.textContent = 'P alv';
    const t0 = E('text', { x: 497, y: 106, 'font-size': 11, fill: '#6b7896', 'text-anchor': 'end', 'font-family': 'Inter' }); t0.textContent = '0 = atmospheric';
    const X = t => 40 + t / 8 * 455;
    const vp = [], pp = [];
    for (let t = 0; t <= 8.001; t += 0.05) {
      vp.push([X(t), 70 - 50 * this.s(t)]);
      const dp = t < 4.4 ? Math.sin(Math.PI * c.seg(t, 0.8, 3.6)) * -1 : Math.sin(Math.PI * c.seg(t, 4.5, 7.4));
      pp.push([X(t), 110 - 26 * dp]);
    }
    this.vl = E('path', { d: 'M' + vp.map(p => p.join(',')).join('L'), fill: 'none', stroke: '#c2417a', 'stroke-width': 3.5, 'stroke-linecap': 'round' });
    this.pl = E('path', { d: 'M' + pp.map(p => p.join(',')).join('L'), fill: 'none', stroke: '#0b6aa2', 'stroke-width': 3.5, 'stroke-linecap': 'round' });
    this.vl._len = this.vl.getTotalLength(); this.pl._len = this.pl.getTotalLength();
    this.cur = E('line', { y1: 10, y2: 140, stroke: '#13203a', 'stroke-width': 1.5, opacity: .35 });
    this.minus = E('text', { x: X(2.2), y: 146, 'font-size': 12, 'font-weight': 700, fill: '#0b6aa2', 'text-anchor': 'middle', 'font-family': 'Inter' }); this.minus.textContent = '≈ −1 cmH₂O';
    this.plus = E('text', { x: X(5.95), y: 76, 'font-size': 12, 'font-weight': 700, fill: '#0b6aa2', 'text-anchor': 'middle', 'font-family': 'Inter' }); this.plus.textContent = '≈ +1 cmH₂O';
    this.X = X;
  },

  update(t, c) {
    // quick swap between the two drawings, plus a gentle size change that follows lung volume
    const x = t < 4.4 ? c.ease(c.seg(t, 1.3, 1.8)) : 1 - c.ease(c.seg(t, 5.0, 5.5));
    c.imgs.ins.style.opacity = x; c.imgs.exp.style.opacity = 1 - x;
    const k = 1 + .035 * this.s(t);
    for (const im of [c.imgs.ins, c.imgs.exp]) { im.style.transformOrigin = '450px 380px'; im.style.transform = `scale(${k}, ${1 + .02 * this.s(t)})`; }
    const inspiring = t > 0.8 && t < 3.8, expiring = t > 4.5 && t < 7.6;
    this.ribs.setAttribute('opacity', c.win(t, 0.8, 3.8) * (.5 + .5 * c.pulse(t, .7)));
    this.lRib.setAttribute('opacity', c.win(t, 0.8, 3.8));
    this.lDia.setAttribute('opacity', c.win(t, 0.8, 4.0));
    this.lDia2.setAttribute('opacity', c.win(t, 4.5, 7.9));
    this.lAir.setAttribute('opacity', c.win(t, 1.4, 4.0));
    this.lAir2.setAttribute('opacity', c.win(t, 5.0, 7.8));
    const flow = Math.max(c.win(t, 1.2, 3.9, .4), c.win(t, 4.8, 7.6, .4));
    this.air.forEach((a, i) => {
      const u = c.frac(t * 0.9 + i / this.air.length);
      const y = inspiring || t < 4.4 ? 70 + u * 150 : 220 - u * 150;
      c.set(a, { cx: 450 + 18 * Math.sin(i * 2.1), cy: y, opacity: flow * Math.min(1, u * 4, (1 - u) * 4) });
    });
    // traces
    const u = t / 8;
    c.reveal(this.vl, u); c.reveal(this.pl, u);
    c.set(this.cur, { x1: this.X(t), x2: this.X(t) });
    this.minus.setAttribute('opacity', c.seg(t, 2.0, 2.3));
    this.plus.setAttribute('opacity', c.seg(t, 5.8, 6.1));
  },
};
