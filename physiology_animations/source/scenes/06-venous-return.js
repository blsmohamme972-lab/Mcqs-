window.SCENE = {
  num: 6, system: 'Cardiovascular', color: '#2563c9',
  title: 'The skeletal muscle pump',
  layers: { v: '01_Cardiovascular/venous-return-1.svg' },
  steps: [
    { t0: 0.3, t1: 1.6, text: 'Calf muscles <b>contract</b> and squeeze the deep vein between them.' },
    { t0: 1.6, t1: 3.8, text: 'Blood is forced <b>upward</b> through the open proximal valve, toward the heart.' },
    { t0: 2.4, t1: 3.8, text: 'The distal valve <b>snaps shut</b> — no backflow.' },
    { t0: 4.2, t1: 8.0, text: 'Muscles <b>relax</b>: pressure falls and the segment <b>refills from below</b> and from tributaries.' },
  ],
  widget: `<div class="wcard"><div class="chips"><span class="chip" id="c1">CONTRACT</span><span class="chip" id="c2">RELAX</span></div>
    <div class="meter" style="margin-top:10px"><span class="lab">Muscle tension</span><span class="trk"><i id="mT" style="background:#e07a5f"></i></span><span class="val" id="vT"></span></div></div>`,
  takeaway: { t: 6.0, text: 'Incompetent valves → venous pooling → varicose veins; immobility removes the pump → DVT risk.' },

  init(c) {
    const o = c.o;
    this.mL = c.el('ellipse', { cx: 355, cy: 315, rx: 58, ry: 175, fill: '#ff7043', filter: 'url(#soft)', opacity: 0 }, o);
    this.mR = c.el('ellipse', { cx: 545, cy: 315, rx: 58, ry: 175, fill: '#ff7043', filter: 'url(#soft)', opacity: 0 }, o);
    const arr = { stroke: '#1f2a44', 'stroke-width': 8, 'marker-end': 'url(#ah)', 'stroke-linecap': 'round' };
    this.sq = c.el('g', {}, o);
    for (const y of [230, 330]) {
      c.el('line', Object.assign({ x1: 270, y1: y, x2: 345, y2: y }, arr), this.sq);
      c.el('line', Object.assign({ x1: 630, y1: y, x2: 555, y2: y }, arr), this.sq);
    }
    this.rel = c.el('g', {}, o);
    for (const y of [230, 330]) {
      c.el('line', Object.assign({ x1: 340, y1: y, x2: 275, y2: y }, arr), this.rel);
      c.el('line', Object.assign({ x1: 560, y1: y, x2: 625, y2: y }, arr), this.rel);
    }
    this.up = c.path([[450, 360], [450, 250], [450, 140], [450, 60], [450, -20]], {}, o);
    this.drops = Array.from({ length: 9 }, () => c.el('ellipse', { rx: 11, ry: 16, fill: '#c62828', stroke: '#fff', 'stroke-width': 3 }, o));
    this.ref = [
      c.path([[320, 735], [380, 705], [430, 660], [450, 600]], {}, o),
      c.path([[555, 712], [505, 690], [465, 650], [450, 600]], {}, o),
      c.path([[548, 868], [505, 845], [460, 780], [450, 700], [450, 600]], {}, o),
      c.path([[450, 900], [450, 780], [450, 600]], {}, o),
    ];
    this.rdrops = [];
    this.ref.forEach(p => { for (let i = 0; i < 3; i++) this.rdrops.push({ p, k: i / 3, e: c.el('ellipse', { rx: 10, ry: 14, fill: '#1e5fbf', stroke: '#fff', 'stroke-width': 3 }, o) }); });
    this.valveX = c.el('g', { opacity: 0 }, o);
    c.el('circle', { cx: 450, cy: 455, r: 54, fill: 'none', stroke: '#e53935', 'stroke-width': 7 }, this.valveX);
    this.lUp = c.label(650, 90, 'Valve open ↑', { lx: 490, ly: 120, color: '#1b7a3a' });
    this.lShut = c.label(700, 460, 'Valve closed', { lx: 505, ly: 455, color: '#c62828' });
    this.lBF = c.label(700, 520, 'no backflow', { color: '#c62828', size: 20 });
    this.lRef = c.label(250, 620, 'Refilling', { color: '#1e5fbf' });
    this.lM = c.label(180, 120, 'Calf muscle', { lx: 320, ly: 220, color: '#b4532a' });
  },

  update(t, c) {
    const { set, seg, win } = c;
    const T = win(t, .3, 4.1, .4);
    set(this.mL, { opacity: .45 * T }); set(this.mR, { opacity: .45 * T });
    this.sq.setAttribute('opacity', T * (.55 + .45 * c.pulse(t, .6)));
    this.rel.setAttribute('opacity', win(t, 4.3, 7.4, .4) * .8);
    this.drops.forEach((d, i) => {
      const u = c.frac((t - 1.2) * .55 + i / 9); const [x, y] = c.at(this.up, u);
      set(d, { cx: x + 10 * Math.sin(i * 1.7) * (1 - u), cy: y, opacity: win(t, 1.3, 4.2, .4) * Math.min(1, u * 6, (1 - u) * 6) });
    });
    this.rdrops.forEach(d => {
      const u = c.frac((t - 4.3) * .45 + d.k); const [x, y] = c.at(d.p, u);
      set(d.e, { cx: x, cy: y, opacity: win(t, 4.3, 7.9, .4) * Math.min(1, u * 6, (1 - u) * 6) });
    });
    this.valveX.setAttribute('opacity', win(t, 2.4, 4.1, .2) * (.6 + .4 * c.pulse(t, .5)));
    this.lUp.setAttribute('opacity', win(t, 1.6, 4.1));
    this.lShut.setAttribute('opacity', win(t, 2.4, 4.1));
    this.lBF.setAttribute('opacity', win(t, 2.6, 4.1));
    this.lRef.setAttribute('opacity', win(t, 4.6, 7.9));
    this.lM.setAttribute('opacity', win(t, .3, 7.9));
    const ten = t < 4 ? c.easeOut(seg(t, .3, 1.2)) : 1 - c.ease(seg(t, 4.0, 4.8));
    document.getElementById('mT').style.width = (ten * 100) + '%';
    document.getElementById('vT').textContent = ten > .5 ? 'high' : 'low';
    document.getElementById('c1').classList.toggle('on', t < 4.1);
    document.getElementById('c2').classList.toggle('on', t >= 4.1);
  },
};
