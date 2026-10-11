window.SCENE = {
  num: 1, system: 'Cardiovascular', color: '#d6334c',
  title: 'How the heartbeat spreads',
  layers: { heart: '01_Cardiovascular/heart-nodes-branches-fibers.svg' },
  steps: [
    { t0: 0.2, t1: 1.2, text: '<b>SA node</b> fires — the pacemaker (60–100/min).' },
    { t0: 1.2, t1: 2.6, text: 'Impulse spreads over both <b>atria</b> = <b>P wave</b>.' },
    { t0: 2.6, t1: 3.8, text: '<b>AV node delay</b> (~0.1 s) lets ventricles fill = <b>PR segment</b>.' },
    { t0: 3.8, t1: 5.6, text: '<b>His → bundle branches → Purkinje</b>: ventricles fire = <b>QRS</b>.' },
    { t0: 5.6, t1: 8.0, text: 'Ventricles repolarise = <b>T wave</b>.' },
  ],
  widget: `<div class="wcard"><div class="wtitle">ECG — Lead II</div><div id="ecg" style="position:relative;width:340px;height:170px;overflow:hidden;margin:0 auto"></div></div>`,
  takeaway: { t: 6.2, text: 'SA → atria → AV node (delay) → His → branches → Purkinje.' },

  init(c) {
    const o = c.o, g = c.el('g', {}, o);
    // atria and ventricles as clip regions for the depolarisation wash
    const d = c.el('defs', {}, o);
    const ca = c.el('clipPath', { id: 'atria' }, d);
    c.path([[150, 390], [235, 375], [330, 400], [350, 520], [330, 610], [240, 640], [160, 600], [135, 480]], {}, ca, true);
    c.path([[500, 270], [585, 255], [655, 300], [655, 380], [600, 420], [520, 400]], {}, ca, true);
    const cv = c.el('clipPath', { id: 'vent' }, d);
    c.path([[340, 560], [470, 525], [560, 470], [700, 455], [760, 600], [745, 790], [610, 880], [410, 865], [255, 790], [235, 690]], {}, cv, true);

    this.aw = c.el('circle', { cx: 210, cy: 340, r: 0, fill: '#ffd23f', 'clip-path': 'url(#atria)', opacity: .5 }, g);
    this.vw = c.el('circle', { cx: 470, cy: 560, r: 0, fill: '#ffd23f', 'clip-path': 'url(#vent)', opacity: .5 }, g);

    // conduction routes
    const gl = { stroke: '#ffe066', 'stroke-width': 9, 'stroke-linecap': 'round', filter: 'url(#glow)' };
    this.intern = c.path([[212, 345], [240, 400], [285, 455], [318, 520]], gl, g);
    this.bach = c.path([[235, 335], [330, 378], [395, 345], [445, 275], [520, 240], [580, 258], [598, 300]], gl, g);
    this.his = c.path([[330, 532], [400, 547], [465, 537]], gl, g);
    this.lbb = c.path([[465, 540], [530, 610], [570, 650], [600, 705], [630, 760], [660, 800], [700, 812], [735, 760], [745, 640], [735, 520]], gl, g);
    this.rbb = c.path([[465, 540], [485, 556], [520, 605], [550, 665], [550, 705], [537, 740], [510, 770], [470, 782], [425, 762], [400, 735]], gl, g);
    [this.intern, this.bach, this.his, this.lbb, this.rbb].forEach(p => c.reveal(p, 0));

    this.sa = c.el('circle', { cx: 210, cy: 340, r: 30, fill: '#fff3b0', filter: 'url(#glow)', opacity: 0 }, g);
    this.av = c.el('circle', { cx: 325, cy: 532, r: 30, fill: '#fff3b0', filter: 'url(#glow)', opacity: 0 }, g);

    this.lSA = c.label(100, 270, 'SA node', { lx: 195, ly: 335, color: '#7a2f8f' });
    this.lAV = c.label(160, 700, 'AV node', { lx: 318, ly: 540, color: '#1b7a3a' });
    this.lHis = c.label(420, 470, 'Bundle of His', { lx: 420, ly: 545, color: '#b8860b' });
    this.lPk = c.label(700, 890 - 40, 'Purkinje fibres', { lx: 640, ly: 800, color: '#a3203a' });

    // ECG inset built from the ECG SVG, cropped to the trace
    const host = document.getElementById('ecg');
    const crop = [108, 150, 960]; // x, y, width of the 900-space shown in the 340px box
    const e = c.stageBox(host, 340, crop, { ecg: '01_Cardiovascular/electrocardiogram-ecg.svg' });
    this.cover = c.el('rect', { x: 137, y: 150, width: 900, height: 520, fill: '#fff' }, e.svg);
    this.dot = c.el('circle', { r: 11, fill: '#d6334c', filter: 'url(#glow)' }, e.svg);
    // ECG polyline (900-space) to place the pen dot
    this.ecgPts = [[137, 517], [240, 517], [255, 470], [270, 447], [285, 465], [297, 512], [350, 512], [362, 590], [409, 207], [459, 602], [476, 530], [617, 530], [640, 470], [662, 415], [683, 416], [705, 470], [727, 530], [737, 530], [760, 512], [780, 507], [800, 515], [815, 530], [900, 530]];
  },

  penX(t) { // map time → x on the trace, so waves line up with the narration
    const k = [[0, 137], [1.2, 240], [2.6, 297], [3.8, 350], [5.0, 476], [5.6, 617], [7.0, 737], [8, 900]];
    for (let i = 1; i < k.length; i++) if (t <= k[i][0]) return k[i - 1][1] + (k[i][1] - k[i - 1][1]) * (t - k[i - 1][0]) / (k[i][0] - k[i - 1][0]);
    return 900;
  },

  update(t, c) {
    const { seg, win, pulse, set } = c;
    set(this.sa, { opacity: Math.max(win(t, .1, 1.6) * (.55 + .45 * pulse(t, .5)), .25 * seg(t, .1, .4)), r: 26 + 10 * pulse(t, .5) });
    set(this.aw, { r: 520 * c.easeOut(seg(t, 1.1, 2.4)), opacity: .55 * win(t, 1.1, 3.1, .5) });
    c.reveal(this.intern, seg(t, 1.1, 2.4)); this.intern.style.opacity = win(t, 1.1, 4.0, .5);
    c.reveal(this.bach, seg(t, 1.1, 2.2)); this.bach.style.opacity = win(t, 1.1, 3.4, .5);
    set(this.av, { opacity: win(t, 2.4, 4.0) * (.5 + .5 * pulse(t - 2.4, .6)), r: 24 + 8 * pulse(t - 2.4, .6) });
    c.reveal(this.his, seg(t, 3.8, 4.2));
    c.reveal(this.lbb, seg(t, 4.15, 5.1)); c.reveal(this.rbb, seg(t, 4.15, 5.0));
    const pk = win(t, 3.8, 6.6, .5);
    [this.his, this.lbb, this.rbb].forEach(p => p.style.opacity = pk);
    set(this.vw, { r: 480 * c.easeOut(seg(t, 4.5, 5.5)), opacity: .55 * win(t, 4.5, 7.2, .8), fill: c.mix('#ffd23f', '#7fb3ff', seg(t, 5.6, 6.8)) });

    this.lSA.setAttribute('opacity', seg(t, .2, .5));
    this.lAV.setAttribute('opacity', seg(t, 2.6, 2.9));
    this.lHis.setAttribute('opacity', seg(t, 3.8, 4.1));
    this.lPk.setAttribute('opacity', seg(t, 4.6, 4.9));

    // ECG
    const x = this.penX(t);
    set(this.cover, { x: x + 4 });
    const P = this.ecgPts; let y = 517;
    for (let i = 1; i < P.length; i++) if (x <= P[i][0]) { const u = (x - P[i - 1][0]) / (P[i][0] - P[i - 1][0]); y = P[i - 1][1] + (P[i][1] - P[i - 1][1]) * u; break; }
    set(this.dot, { cx: x, cy: y });
  },
};
