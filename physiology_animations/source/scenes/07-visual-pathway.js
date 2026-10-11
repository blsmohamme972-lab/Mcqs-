window.SCENE = {
  num: 7, system: 'Special senses', color: '#7c3aed',
  title: 'The visual pathway',
  layers: { v: '05_Nervous_and_Senses/optical-pathway.svg' },
  view: [0, 40, 880],
  steps: [
    { t0: 0.2, t1: 1.6, text: 'Light from the <b>right visual field</b> lands on the left <b>temporal</b> and right <b>nasal</b> retina.' },
    { t0: 1.6, t1: 3.4, text: 'At the <b>optic chiasm</b> only <b>nasal</b> fibres cross; temporal fibres stay on their side.' },
    { t0: 3.4, t1: 4.6, text: 'The <b>optic tract</b> carries both to the <b>lateral geniculate nucleus</b> (thalamus).' },
    { t0: 4.6, t1: 8.0, text: '<b>Optic radiations</b> reach the <b>visual cortex</b>: each hemisphere sees the <b>opposite</b> half of the world.' },
  ],
  widget: `<div class="wcard"><div class="wtitle">Lesion → field defect</div>
    <div style="display:grid;grid-template-columns:auto 1fr;gap:4px 14px;font:500 14px/1.35 Inter;color:#22304d">
    <b>Optic nerve</b><span>Monocular blindness</span>
    <b style="color:#7c3aed">Optic chiasm</b><span style="color:#7c3aed;font-weight:600">Bitemporal hemianopia</span>
    <b>Optic tract</b><span>Contralateral homonymous hemianopia</span></div></div>`,
  takeaway: { t: 6.2, text: 'Pituitary adenoma compresses the chiasm → the crossing nasal fibres are hit → bitemporal hemianopia.' },

  init(c) {
    const o = c.o;
    const Y = { stroke: '#ffcf33', 'stroke-width': 13, 'stroke-linecap': 'round', filter: 'url(#glow)' };
    const M = { stroke: '#e0359a', 'stroke-width': 13, 'stroke-linecap': 'round', filter: 'url(#glow)' };
    // light rays from the right visual field (yellow bar) through each pupil to the retina
    this.rays = c.el('g', { opacity: 0 }, o);
    const ray = (a, b) => c.el('line', { x1: a[0], y1: a[1], x2: b[0], y2: b[1], stroke: '#f5b800', 'stroke-width': 4, 'stroke-dasharray': '10 8' }, this.rays);
    ray([470, 104], [200, 158]); ray([200, 158], [175, 220]);
    ray([470, 104], [418, 158]); ray([418, 158], [398, 222]);
    this.fieldR = c.el('rect', { x: 328, y: 96, width: 212, height: 16, rx: 4, fill: '#ffe066', filter: 'url(#glow)', opacity: 0 }, o);
    this.yA = c.path([[188, 232], [212, 300], [248, 390], [283, 450], [275, 500], [256, 545], [244, 576]], Y, o);
    this.yB = c.path([[402, 232], [386, 300], [356, 390], [318, 442], [290, 472], [270, 520], [262, 560], [262, 590]], Y, o);
    this.yR = c.path([[244, 590], [232, 645], [250, 705], [290, 765]], Y, o);
    this.mA = c.path([[424, 232], [400, 310], [366, 400], [345, 450], [355, 500], [370, 545], [382, 576]], M, o);
    this.mB = c.path([[206, 232], [230, 310], [264, 400], [300, 445], [330, 470], [350, 520], [357, 560], [357, 590]], M, o);
    this.mR = c.path([[378, 590], [388, 650], [370, 720], [336, 765]], M, o);
    [this.yA, this.yB, this.yR, this.mA, this.mB, this.mR].forEach(p => c.reveal(p, 0));
    this.lgnL = c.el('circle', { cx: 250, cy: 588, r: 26, fill: '#fff176', filter: 'url(#glow)', opacity: 0 }, o);
    this.cortexL = c.path([[180, 735], [215, 760], [260, 790], [298, 785], [300, 700], [292, 650]], { fill: '#ffe066', opacity: 0, filter: 'url(#soft)' }, o, true);
    this.cortexR = c.path([[318, 650], [312, 720], [325, 785], [375, 780], [410, 760], [430, 735]], { fill: '#f48fc4', opacity: 0, filter: 'url(#soft)' }, o, true);
    this.lCross = c.label(470, 420, 'Nasal fibres cross', { lx: 305, ly: 455, color: '#1f2a44', size: 22 });
    this.lLGN = c.label(110, 520, 'LGN', { lx: 245, ly: 585, color: '#8d6e00', size: 22 });
    this.lCtx = c.label(130, 840, 'Left visual cortex sees the RIGHT field', { color: '#8d6e00', size: 21 });
    this.lCtx.setAttribute('transform', 'translate(110,0)');
  },

  update(t, c) {
    const { seg, win } = c;
    this.fieldR.setAttribute('opacity', win(t, .1, 8.2) * (.5 + .5 * c.pulse(t, 1)));
    this.rays.setAttribute('opacity', win(t, .3, 2.2));
    this.rays.style.strokeDashoffset = -t * 40;
    [...this.rays.children].forEach(l => l.style.strokeDashoffset = -t * 40);
    c.reveal(this.yA, seg(t, 1.2, 3.4)); c.reveal(this.yB, seg(t, 1.2, 3.4));
    this.lgnL.setAttribute('opacity', win(t, 3.4, 5.4) * (.6 + .4 * c.pulse(t, .5)));
    c.reveal(this.yR, seg(t, 4.4, 5.6));
    this.cortexL.setAttribute('opacity', .75 * seg(t, 5.4, 6.0));
    // mirror pathway (left field → right cortex), shown faster for symmetry
    const m = seg(t, 5.6, 6.0);
    [this.mA, this.mB, this.mR].forEach(p => p.style.opacity = .85 * m);
    c.reveal(this.mA, seg(t, 5.6, 6.8)); c.reveal(this.mB, seg(t, 5.6, 6.8)); c.reveal(this.mR, seg(t, 6.6, 7.3));
    this.cortexR.setAttribute('opacity', .7 * seg(t, 7.2, 7.6));
    this.lCross.setAttribute('opacity', seg(t, 2.0, 2.3));
    this.lLGN.setAttribute('opacity', seg(t, 3.5, 3.8));
    this.lCtx.setAttribute('opacity', seg(t, 5.5, 5.9));
  },
};
