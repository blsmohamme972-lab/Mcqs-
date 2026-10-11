window.SCENE = {
  num: 10, system: 'Renal', color: '#b5541c',
  title: 'From filtrate to urine',
  layers: { n: '03_Renal/nephron_2d.svg' },
  steps: [
    { t0: 0.2, t1: 1.5, text: '<b>Glomerulus</b> filters plasma into Bowman’s capsule — GFR ≈ 125 mL/min (180 L/day).' },
    { t0: 1.5, t1: 3.3, text: '<b>Proximal tubule</b> reabsorbs ~65% of Na⁺ and water, and all glucose & amino acids.' },
    { t0: 3.3, t1: 5.3, text: '<b>Loop of Henle:</b> descending limb loses water; ascending limb pumps out NaCl but is water-tight.' },
    { t0: 5.3, t1: 8.0, text: '<b>DCT & collecting duct</b> fine-tune: aldosterone (Na⁺) and <b>ADH</b> (water) → ~1.5 L urine/day.' },
  ],
  widget: `<div class="wcard"><div class="meter"><span class="lab">Filtrate left</span><span class="trk"><i id="mV" style="background:#e3b21b"></i></span><span class="val" id="vV"></span></div></div>`,
  takeaway: { t: 6.8, text: '~99% of filtered water is reclaimed. No ADH (diabetes insipidus) → large volumes of dilute urine.' },

  init(c) {
    const o = c.o;
    const F = { stroke: '#f2c230', 'stroke-width': 18, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', opacity: .55 };
    this.glo = c.el('circle', { cx: 345, cy: 118, r: 62, fill: '#ff5252', filter: 'url(#soft)', opacity: 0 }, o);
    this.pct = c.path([[300, 200], [245, 178], [190, 190], [182, 228], [212, 250], [240, 272], [218, 305], [228, 350], [268, 362], [302, 340], [320, 285], [348, 268], [385, 300], [393, 360], [394, 470]], F, o);
    this.loop = c.path([[394, 470], [393, 650], [395, 850], [418, 888], [440, 862], [445, 780], [432, 690], [438, 520], [440, 240]], F, o);
    this.dct = c.path([[440, 240], [470, 215], [496, 178], [495, 130], [463, 95], [470, 55], [510, 45], [530, 72], [530, 105], [575, 110], [604, 117], [590, 150], [575, 182], [620, 202], [688, 202], [714, 240], [715, 330], [716, 425]], F, o);
    [this.pct, this.loop, this.dct].forEach(p => c.reveal(p, 0));
    // reabsorption arrows: [x, y, dx, color]
    const A = (x, y, dx, col, g) => c.el('line', { x1: x, y1: y, x2: x + dx, y2: y, stroke: col, 'stroke-width': 8, 'marker-end': 'url(#ah)', 'stroke-linecap': 'round' }, g);
    this.aP = c.el('g', { opacity: 0 }, o); A(170, 230, -60, '#29a8e0', this.aP); A(215, 330, -60, '#29a8e0', this.aP); A(395, 330, 70, '#29a8e0', this.aP);
    this.aD = c.el('g', { opacity: 0 }, o); A(380, 560, -70, '#29a8e0', this.aD); A(382, 690, -70, '#29a8e0', this.aD); A(384, 800, -70, '#29a8e0', this.aD);
    this.aA = c.el('g', { opacity: 0 }, o); A(472, 600, 70, '#ff8a00', this.aA); A(470, 460, 70, '#ff8a00', this.aA); A(468, 330, 70, '#ff8a00', this.aA);
    this.aC = c.el('g', { opacity: 0 }, o); A(745, 300, 70, '#29a8e0', this.aC); A(745, 380, 70, '#29a8e0', this.aC);
    this.drops = Array.from({ length: 4 }, () => c.el('ellipse', { rx: 9, ry: 13, fill: '#f2c230', stroke: '#b58a00', 'stroke-width': 3 }, o));
    this.lG = c.label(240, 40, 'Glomerulus', { lx: 330, ly: 110, color: '#c62828', size: 23 });
    this.lP = c.label(110, 430, 'PCT', { lx: 200, ly: 300, color: '#1f2a44', size: 23 });
    this.lH2O = c.label(260, 625, 'H₂O out', { color: '#1a87bd', size: 22 });
    this.lNa = c.label(590, 530, 'NaCl out', { color: '#e07000', size: 22 });
    this.lADH = c.label(800, 250, 'ADH', { color: '#1a87bd', size: 23 });
    this.lU = c.label(715, 520, 'Urine', { color: '#b58a00', size: 23 });
  },

  update(t, c) {
    const { seg, win, set } = c;
    set(this.glo, { opacity: .5 * win(t, .2, 1.8) * (.6 + .4 * c.pulse(t, .5)) });
    c.reveal(this.pct, seg(t, .9, 3.0)); c.reveal(this.loop, seg(t, 3.0, 5.0)); c.reveal(this.dct, seg(t, 5.0, 7.0));
    // filtrate thins as water is reabsorbed
    this.pct.setAttribute('stroke-width', 18); this.loop.setAttribute('stroke-width', 13); this.dct.setAttribute('stroke-width', 8);
    this.aP.setAttribute('opacity', win(t, 1.8, 3.6) * (.6 + .4 * c.pulse(t, .6)));
    this.aD.setAttribute('opacity', win(t, 3.3, 5.4) * (.6 + .4 * c.pulse(t, .6)));
    this.aA.setAttribute('opacity', win(t, 4.2, 5.8) * (.6 + .4 * c.pulse(t, .6)));
    this.aC.setAttribute('opacity', win(t, 6.0, 8.2) * (.6 + .4 * c.pulse(t, .6)));
    this.drops.forEach((d, i) => { const u = c.frac((t - 7.0) * .9 + i / 4); set(d, { cx: 716, cy: 430 + u * 60, opacity: win(t, 7.0, 8.2, .2) * (1 - u) }); });
    this.lG.setAttribute('opacity', seg(t, .2, .5));
    this.lP.setAttribute('opacity', seg(t, 1.6, 1.9));
    this.lH2O.setAttribute('opacity', win(t, 3.4, 5.4));
    this.lNa.setAttribute('opacity', win(t, 4.2, 5.9));
    this.lADH.setAttribute('opacity', seg(t, 6.0, 6.3));
    this.lU.setAttribute('opacity', seg(t, 7.1, 7.4));
    const keys = [[0, 100], [1.0, 100], [3.0, 35], [5.0, 20], [7.2, 1], [8, 1]];
    let v = 100; for (let i = 1; i < keys.length; i++) if (t <= keys[i][0]) { v = c.lerp(keys[i - 1][1], keys[i][1], c.ease((t - keys[i - 1][0]) / (keys[i][0] - keys[i - 1][0]))); break; } else v = keys[i][1];
    document.getElementById('mV').style.width = v + '%';
    document.getElementById('vV').textContent = (v < 2 ? '~1' : Math.round(v)) + '%';
  },
};
