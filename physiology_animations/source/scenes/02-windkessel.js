window.SCENE = {
  num: 2, system: 'Cardiovascular', color: '#e0582f',
  title: 'The aorta as a second pump',
  layers: { sys: '01_Cardiovascular/systole.svg', dia: '01_Cardiovascular/diastole.svg' },
  steps: [
    { t0: 0.2, t1: 1.6, text: '<b>Systole:</b> the left ventricle contracts and the <b>aortic valve opens</b>.' },
    { t0: 1.6, t1: 3.6, text: 'Blood is ejected faster than it can run off — the elastic <b>aorta stretches</b> and stores energy.' },
    { t0: 3.6, t1: 5.6, text: '<b>Diastole:</b> the aortic valve <b>closes</b>; the ventricle relaxes and refills.' },
    { t0: 5.6, t1: 8.0, text: '<b>Elastic recoil</b> of the aorta keeps blood flowing forward — flow stays continuous.' },
  ],
  widget: `<div class="wcard">
    <div class="chips" style="margin-bottom:10px"><span class="chip" id="cS">SYSTOLE</span><span class="chip" id="cD">DIASTOLE</span></div>
    <div class="meter"><span class="lab">Aortic stretch</span><span class="trk"><i id="mE" style="background:#e0582f"></i></span><span class="val" id="vE"></span></div>
    <div class="meter"><span class="lab">Flow to tissues</span><span class="trk"><i id="mF" style="background:#2f7de0"></i></span><span class="val" id="vF"></span></div>
  </div>`,
  takeaway: { t: 6.4, text: 'Windkessel effect: aortic elasticity turns pulsatile ejection into continuous flow and keeps diastolic pressure up. Stiff aorta (ageing) → ↑ systolic & pulse pressure.' },

  init(c) {
    const o = c.o;
    this.gs = c.el('g', {}, o); this.gd = c.el('g', {}, o);
    this.pS = c.path([[290, 390], [330, 325], [420, 290], [600, 285], [880, 285]], {}, this.gs);
    this.pD = c.path([[400, 262], [600, 258], [880, 260]], {}, this.gd);
    this.pFill = c.path([[170, 285], [205, 345], [250, 410], [260, 520]], {}, this.gd);
    const rbc = (g, n) => Array.from({ length: n }, () => c.el('ellipse', { rx: 13, ry: 8, fill: '#ffd6cc', stroke: '#9c1c1c', 'stroke-width': 3 }, g));
    this.dS = rbc(this.gs, 9); this.dD = rbc(this.gd, 6); this.dF = rbc(this.gd, 4);
    // stretch arrows on the aortic wall (systole)
    const arr = { stroke: '#1f2a44', 'stroke-width': 6, 'marker-end': 'url(#ah)', 'stroke-linecap': 'round' };
    this.out = c.el('g', {}, this.gs);
    for (const x of [470, 560, 650]) { c.el('line', Object.assign({ x1: x, y1: 185, x2: x, y2: 135 }, arr), this.out); c.el('line', Object.assign({ x1: x, y1: 425, x2: x, y2: 475 }, arr), this.out); }
    this.lOpen = c.label(330, 140, 'Aortic valve OPEN', { lx: 320, ly: 300, color: '#1b7a3a' });
    this.lClosed = c.label(330, 140, 'Aortic valve CLOSED', { lx: 300, ly: 265, color: '#a3203a' });
    this.lStretch = c.label(600, 520, 'Aorta stretches', { color: '#c2410c' });
    this.lRecoil = c.label(600, 450, 'Elastic recoil', { color: '#1d4ed8' });
    this.lLV = c.label(160, 800, 'Left ventricle', { lx: 230, ly: 600, color: '#1f2a44' });
  },

  update(t, c) {
    const x = c.ease(c.seg(t, 3.5, 4.4));
    c.imgs.sys.style.opacity = 1 - x; c.imgs.dia.style.opacity = x;
    this.gs.setAttribute('opacity', 1 - x); this.gd.setAttribute('opacity', x);
    // speeds: fast during systolic ejection, moderate steady in diastole
    const phS = c.integ(s => s < 3.6 ? 0.45 * (0.4 + 0.6 * c.pulse(Math.min(s, 3.6), 7.2)) : 0.2, t);
    this.dS.forEach((d, i) => { const [px, py] = c.at(this.pS, c.frac(phS + i / this.dS.length)); c.set(d, { cx: px, cy: py }); });
    const phD = 0.22 * t;
    this.dD.forEach((d, i) => { const [px, py] = c.at(this.pD, c.frac(phD + i / this.dD.length)); c.set(d, { cx: px, cy: py }); });
    this.dF.forEach((d, i) => { const u = c.frac(0.3 * t + i / this.dF.length); const [px, py] = c.at(this.pFill, u); c.set(d, { cx: px, cy: py, opacity: Math.min(u * 5, (1 - u) * 5, 1) }); });
    this.out.setAttribute('opacity', c.win(t, 1.4, 3.7) * (.6 + .4 * c.pulse(t, .8)));
    this.lOpen.setAttribute('opacity', c.win(t, .3, 3.6));
    this.lClosed.setAttribute('opacity', c.seg(t, 4.3, 4.6));
    this.lStretch.setAttribute('opacity', c.win(t, 1.7, 3.6));
    this.lRecoil.setAttribute('opacity', c.seg(t, 5.6, 5.9));
    this.lLV.setAttribute('opacity', c.win(t, .2, 3.4));
    // widget
    const E = t < 3.6 ? c.easeOut(c.seg(t, .4, 3.4)) * .9 : .9 - .65 * c.ease(c.seg(t, 4.0, 7.8));
    const F = t < 3.6 ? .55 + .4 * c.seg(t, .4, 1.6) : .95 - .25 * c.seg(t, 4.0, 7.8);
    document.getElementById('mE').style.width = (E * 100) + '%';
    document.getElementById('vE').textContent = Math.round(E * 100) + '%';
    document.getElementById('mF').style.width = (F * 100) + '%';
    document.getElementById('vF').textContent = 'continuous';
    document.getElementById('cS').classList.toggle('on', t < 3.9);
    document.getElementById('cD').classList.toggle('on', t >= 3.9);
  },
};
