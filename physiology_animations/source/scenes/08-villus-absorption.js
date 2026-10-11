window.SCENE = {
  num: 8, system: 'Digestive', color: '#e07a1f',
  title: 'Absorption in the villus',
  layers: { v: '04_Digestive/intestinal-villi.svg' },
  view: [0, 30, 900],
  steps: [
    { t0: 0.2, t1: 1.6, text: '<b>Villi</b> and microvilli multiply the absorptive surface of the small intestine.' },
    { t0: 1.6, t1: 4.2, text: '<b>Monosaccharides & amino acids</b> cross the enterocyte into the <b>blood capillaries</b>.' },
    { t0: 4.2, t1: 6.4, text: '<b>Fats</b> are packed into <b>chylomicrons</b> — too big for capillaries — and enter the <b>lacteal</b>.' },
    { t0: 6.4, t1: 8.0, text: 'Blood → <b>hepatic portal vein → liver</b>. Lymph → <b>thoracic duct</b>, bypassing the liver.' },
  ],
  widget: `<div class="wcard"><div class="wtitle">Legend</div>
    <div style="display:flex;gap:18px;font:600 14px Inter;color:#22304d;align-items:center">
    <span><svg width="14" height="14"><circle cx="7" cy="7" r="6" fill="#ff7a1a" stroke="#fff"/></svg> Glucose</span>
    <span><svg width="14" height="14"><rect x="1" y="1" width="12" height="12" rx="3" fill="#2bb5a5"/></svg> Amino acid</span>
    <span><svg width="16" height="16"><circle cx="8" cy="8" r="7" fill="#ffd54a" stroke="#c49000" stroke-width="2"/></svg> Chylomicron</span></div></div>`,
  takeaway: { t: 6.8, text: 'Water-soluble nutrients → blood → liver first. Long-chain fats → lacteal → lymph → bloodstream via the thoracic duct.' },

  init(c) {
    const o = c.o;
    // nutrients drifting in the lumen
    this.lumen = Array.from({ length: 16 }, (_, i) => ({ x: 240 + (i * 97) % 420, y: 185 + (i * 37) % 60, k: i, e: i % 3 == 2 ? c.el('circle', { r: 12, fill: '#ffd54a', stroke: '#c49000', 'stroke-width': 3 }, o) : (i % 3 ? c.el('rect', { width: 18, height: 18, rx: 4, fill: '#2bb5a5', stroke: '#fff', 'stroke-width': 2 }, o) : c.el('circle', { r: 9, fill: '#ff7a1a', stroke: '#fff', 'stroke-width': 3 }, o)) }));
    this.blood = [
      c.path([[560, 205], [558, 265], [550, 340], [542, 420], [530, 520], [522, 600], [520, 660]], {}, o),
      c.path([[470, 420], [505, 432], [528, 480], [524, 560], [520, 660]], {}, o),
      c.path([[640, 420], [600, 440], [560, 480], [530, 560], [520, 660]], {}, o),
    ];
    this.lymph = [
      c.path([[300, 205], [303, 265], [302, 340], [298, 450], [300, 560], [302, 660]], {}, o),
      c.path([[420, 450], [380, 470], [335, 515], [304, 600], [302, 660]], {}, o),
      c.path([[225, 450], [255, 480], [285, 540], [300, 600], [302, 660]], {}, o),
    ];
    this.bp = []; this.lp = [];
    this.blood.forEach((p, j) => { for (let i = 0; i < 3; i++) this.bp.push({ p, k: i / 3 + j * .11, e: (i + j) % 2 ? c.el('circle', { r: 10, fill: '#ff7a1a', stroke: '#fff', 'stroke-width': 3 }, o) : c.el('rect', { x: -9, y: -9, width: 18, height: 18, rx: 4, fill: '#2bb5a5', stroke: '#fff', 'stroke-width': 2 }, o) }); });
    this.lymph.forEach((p, j) => { for (let i = 0; i < 3; i++) this.lp.push({ p, k: i / 3 + j * .13, e: c.el('circle', { r: 13, fill: '#ffd54a', stroke: '#c49000', 'stroke-width': 3 }, o) }); });
    this.cap = c.path([[520, 330], [560, 330], [600, 420], [600, 560], [520, 600], [500, 480]], { fill: '#ff3b3b', filter: 'url(#soft)', opacity: 0 }, o, true);
    this.lac = c.path([[290, 330], [320, 330], [345, 480], [315, 620], [290, 620], [265, 480]], { fill: '#7cd65a', filter: 'url(#soft)', opacity: 0 }, o, true);
    this.lPortal = c.label(520, 790, '→ portal vein → liver', { color: '#c62828', size: 22 });
    this.lLymph = c.label(250, 790, '→ lymph', { color: '#3d8b2f', size: 22 });
  },

  update(t, c) {
    const { set, seg, win } = c;
    this.lumen.forEach((n, i) => {
      const x = n.x + 18 * Math.sin(t * 1.3 + i), y = n.y + 10 * Math.cos(t * 1.1 + i * .7);
      const isFat = i % 3 == 2;
      const gone = isFat ? seg(t, 4.4, 5.6) : seg(t, 1.8, 3.2);
      const op = seg(t, .1, .5) * (1 - gone);
      if (n.e.tagName === 'rect') set(n.e, { x: x - 9, y: y - 9, opacity: op }); else set(n.e, { cx: x, cy: y, opacity: op });
    });
    const move = (arr, a, b) => arr.forEach(d => {
      const u = c.frac((t - a) * .42 + d.k); const [x, y] = c.at(d.p, u);
      const op = win(t, a, b, .4) * Math.min(1, u * 7, (1 - u) * 7);
      if (d.e.tagName === 'rect') set(d.e, { x: x - 9, y: y - 9, opacity: op }); else set(d.e, { cx: x, cy: y, opacity: op });
    });
    move(this.bp, 1.7, 8.2); move(this.lp, 4.3, 8.2);
    this.cap.setAttribute('opacity', .35 * win(t, 1.8, 4.6, .4));
    this.lac.setAttribute('opacity', .4 * win(t, 4.3, 6.8, .4));
    this.lPortal.setAttribute('opacity', seg(t, 6.4, 6.7));
    this.lLymph.setAttribute('opacity', seg(t, 6.5, 6.8));
  },
};
