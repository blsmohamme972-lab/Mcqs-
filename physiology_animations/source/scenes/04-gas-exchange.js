window.SCENE = {
  num: 4, system: 'Respiratory', color: '#3b6fd8',
  title: 'Gas exchange in the alveolus',
  layers: { gx: '02_Respiratory/gas-exchange-pulmonary.svg' },
  steps: [
    { t0: 0.2, t1: 1.6, text: '<b>Deoxygenated blood</b> enters the capillary: PO₂ 40, PCO₂ 46 mmHg.' },
    { t0: 1.6, t1: 3.8, text: '<b>O₂ diffuses</b> from alveolar air (PO₂ 100) into blood — down its partial-pressure gradient.' },
    { t0: 3.8, t1: 5.8, text: '<b>CO₂ diffuses</b> the opposite way, from blood (46) into the alveolus (40).' },
    { t0: 5.8, t1: 8.0, text: 'Blood leaves <b>oxygenated</b> — equilibrium in ~0.25 s of the 0.75 s transit time.' },
  ],
  widget: `<div class="wcard"><div class="wtitle">Capillary blood (mmHg)</div>
    <div class="meter"><span class="lab">PO₂</span><span class="trk"><i id="mO" style="background:#d62839"></i></span><span class="val" id="vO"></span></div>
    <div class="meter"><span class="lab">PCO₂</span><span class="trk"><i id="mC" style="background:#7a3fa0"></i></span><span class="val" id="vC"></span></div>
    <div style="font:500 12.5px Inter;color:#6b7896;margin-top:6px">Alveolar air: PO₂ 100 · PCO₂ 40 mmHg</div></div>`,
  takeaway: { t: 6.4, text: "Fick's law: diffusion ∝ area × gradient ÷ thickness. Fibrosis (thick membrane) and emphysema (lost area) both impair exchange." },

  init(c) {
    const o = c.o;
    // blood flows from the blue (bottom) end to the red (top / right) ends
    this.v1 = c.path([[370, 760], [300, 660], [215, 560], [270, 480], [400, 425], [600, 385], [905, 325]], {}, o);
    this.v2 = c.path([[620, 760], [600, 620], [560, 480], [480, 420], [400, 330], [330, 230], [305, 150]], {}, o);
    this.v3 = c.path([[0, 520], [150, 485], [300, 430], [460, 395], [650, 360], [905, 305]], {}, o);
    this.cells = [];
    for (const p of [this.v1, this.v2, this.v3]) for (let i = 0; i < 5; i++) this.cells.push({ p, k: i / 5, e: c.el('ellipse', { rx: 20, ry: 13, 'stroke-width': 4, stroke: '#fff' }, o) });
    // molecules along the drawn arrows
    const mol = (txt, col) => { const g = c.el('g', {}, o); c.el('circle', { r: 21, fill: col, stroke: '#fff', 'stroke-width': 3 }, g); const t = c.el('text', { y: 7, 'text-anchor': 'middle', 'font-size': 19, 'font-weight': 800, fill: '#fff', 'font-family': 'Inter' }, g); t.textContent = txt; return g; };
    this.o2p = [c.path([[440, 530], [330, 605], [170, 590]], {}, o), c.path([[820, 590], [620, 610], [530, 465]], {}, o)]; // alveolus → blood
    this.co2p = [c.path([[330, 372], [170, 360], [55, 215]], {}, o), c.path([[400, 360], [480, 245], [710, 262]], {}, o)];
    this.o2 = []; this.co2 = [];
    this.o2p.forEach(p => { for (let i = 0; i < 3; i++) this.o2.push({ p, k: i / 3, g: mol('O₂', '#1f9bd7') }); });
    this.co2p.forEach(p => { for (let i = 0; i < 3; i++) this.co2.push({ p, k: i / 3, g: mol('CO₂', '#7a3fa0') }); });
    this.lA = c.label(720, 110, 'Alveolar wall', { lx: 800, ly: 210, color: '#b0306a' });
    this.lC = c.label(330, 815, 'Capillary blood', { lx: 370, ly: 730, color: '#3b4cc0' });
  },

  update(t, c) {
    const flowPh = 0.11 * t;
    this.cells.forEach(o => {
      const u = c.frac(flowPh + o.k); const [x, y] = c.at(o.p, u);
      c.set(o.e, { cx: x, cy: y, fill: c.mix('#3c4fc9', '#e0323c', c.clamp(u * 1.6)), opacity: Math.min(1, u * 8, (1 - u) * 8) });
    });
    const run = (arr, a, speed) => arr.forEach(m => {
      const u = c.frac((t - a) * speed + m.k); const [x, y] = c.at(m.p, u);
      m.g.setAttribute('transform', `translate(${x},${y})`);
      m.g.setAttribute('opacity', c.seg(t, a, a + .3) * Math.min(1, u * 6, (1 - u) * 6));
    });
    run(this.o2, 1.6, .5); run(this.co2, 3.8, .5);
    this.lA.setAttribute('opacity', c.seg(t, .2, .5));
    this.lC.setAttribute('opacity', c.seg(t, .3, .6));
    const PO2 = c.lerp(40, 100, c.easeOut(c.seg(t, 1.8, 5.6))), PCO2 = c.lerp(46, 40, c.easeOut(c.seg(t, 3.9, 6.4)));
    document.getElementById('mO').style.width = PO2 + '%';
    document.getElementById('vO').textContent = Math.round(PO2);
    document.getElementById('mC').style.width = (PCO2 / 50 * 100) + '%';
    document.getElementById('vC').textContent = Math.round(PCO2);
  },
};
