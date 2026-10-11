/* Shared engine for the 8-second physiology explainers.
   Stage coordinates: every base SVG is drawn "contain" inside a 900x900 space,
   and the overlay <svg> uses viewBox 0 0 900 900, so overlay points match the art. */
(function () {
  const DUR = 8;
  const NS = 'http://www.w3.org/2000/svg';
  const S = window.SCENE;

  // ---------- math helpers ----------
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const seg = (t, a, b) => clamp((t - a) / (b - a));
  const lerp = (a, b, u) => a + (b - a) * u;
  const ease = u => u < .5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2;
  const easeOut = u => 1 - Math.pow(1 - u, 3);
  const frac = v => v - Math.floor(v);
  // window: fades in over [a, a+f], out over [b-f, b]
  const win = (t, a, b, f = .3) => Math.min(seg(t, a, a + f), 1 - seg(t, b - f, b));
  const pulse = (t, period = 1) => .5 - .5 * Math.cos(2 * Math.PI * t / period);
  const mix = (c1, c2, u) => {
    const p = c => [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16));
    const a = p(c1), b = p(c2);
    return '#' + a.map((v, i) => Math.round(lerp(v, b[i], u)).toString(16).padStart(2, '0')).join('');
  };
  // integrate a speed function from 0..t (keeps particles continuous when speed changes)
  const integ = (fn, t, dt = 1 / 120) => { let s = 0; for (let x = 0; x < t; x += dt) s += fn(x) * Math.min(dt, t - x); return s; };

  // ---------- DOM helpers ----------
  function el(tag, attrs = {}, parent) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function set(e, attrs) { for (const k in attrs) e.setAttribute(k, attrs[k]); return e; }
  // smooth Catmull-Rom path through points
  function smoothD(pts, closed) {
    if (pts.length < 3) return 'M' + pts.map(p => p.join(',')).join('L');
    const P = closed ? [pts[pts.length - 1], ...pts, pts[0], pts[1]] : [pts[0], ...pts, pts[pts.length - 1]];
    let d = 'M' + pts[0].join(',');
    for (let i = 1; i < P.length - 2; i++) {
      const [p0, p1, p2, p3] = [P[i - 1], P[i], P[i + 1], P[i + 2]];
      const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
      const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
      d += `C${c1.join(',')} ${c2.join(',')} ${p2.join(',')}`;
    }
    return d + (closed ? 'Z' : '');
  }
  function path(pts, attrs = {}, parent, closed) {
    const dbg = /debug/.test(location.search) && !attrs.stroke ? { stroke: '#00e676', 'stroke-width': 4 } : {};
    const p = el('path', Object.assign({ d: smoothD(pts, closed), fill: 'none' }, dbg, attrs), parent);
    p._len = p.getTotalLength();
    return p;
  }
  const at = (p, u) => { const q = p.getPointAtLength(clamp(u) * p._len); return [q.x, q.y]; };
  // progressive stroke reveal
  function reveal(p, u) { p.style.strokeDasharray = p._len; p.style.strokeDashoffset = p._len * (1 - clamp(u)); }

  // ---------- page scaffold ----------
  function stageBox(host, size, view, layers) {
    const [vx, vy, vs] = view || [0, 0, 900];
    const k = size / vs;
    const box = document.createElement('div');
    box.className = 'space';
    box.style.transform = `scale(${k}) translate(${-vx}px, ${-vy}px)`;
    const imgs = {};
    for (const name in layers) {
      const img = document.createElement('img');
      img.src = 'data:image/svg+xml;base64,' + window.__L[layers[name]];
      img.className = 'layer';
      box.appendChild(img);
      imgs[name] = img;
    }
    const svg = el('svg', { viewBox: '0 0 900 900', class: 'overlay' });
    svg.innerHTML = `<defs>
      <filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      <filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="14"/></filter>
      <marker id="ah" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse"><path d="M0,0L10,5L0,10z" fill="context-stroke"/></marker>
    </defs>`;
    box.appendChild(svg);
    host.appendChild(box);
    return { imgs, svg };
  }

  const root = document.getElementById('root');
  root.style.setProperty('--accent', S.color);
  root.innerHTML = `
    <div class="stage"><div class="stage-inner" id="stage"></div><div class="badge">${S.num}/10</div></div>
    <div class="panel">
      <div class="kicker">Physiology · ${S.system}</div>
      <h1>${S.title}</h1>
      <ol class="steps">${S.steps.map((s, i) => `<li><span class="n">${i + 1}</span><span class="tx">${s.text}</span></li>`).join('')}</ol>
      <div class="widget" id="widget">${S.widget || ''}</div>
      <div class="take"><b>Key point</b>${S.takeaway.text}</div>
    </div>
    <div class="bar"><i id="prog"></i></div>`;

  const st = stageBox(document.getElementById('stage'), 640, S.view, S.layers);
  const ctx = {
    o: st.svg, imgs: st.imgs, el, set, path, at, reveal, smoothD,
    clamp, seg, lerp, ease, easeOut, frac, win, pulse, mix, integ, NS,
    widget: document.getElementById('widget'), stageBox,
    // pill label with optional leader line to (lx, ly)
    label(x, y, text, opts = {}) {
      const g = el('g', { opacity: 0 }, opts.parent || st.svg);
      if (opts.lx != null) el('line', { x1: x, y1: y, x2: opts.lx, y2: opts.ly, stroke: opts.color || '#1f2a44', 'stroke-width': 2.5 }, g);
      if (opts.lx != null) el('circle', { cx: opts.lx, cy: opts.ly, r: 5, fill: opts.color || '#1f2a44' }, g);
      const fs = opts.size || 25;
      const t = el('text', { x, y: y + fs * .35, 'font-size': fs, 'font-weight': 650, fill: '#fff', 'text-anchor': 'middle', 'font-family': 'Inter, sans-serif' }, g);
      t.textContent = text;
      const w = text.length * fs * .56 + 26, h = fs + 16;
      const r = el('rect', { x: x - w / 2, y: y - h / 2, width: w, height: h, rx: h / 2, fill: opts.color || '#1f2a44' }, g);
      g.insertBefore(r, t);
      return g;
    },
  };
  S.init && S.init(ctx);

  const lis = [...document.querySelectorAll('.steps li')];
  const take = document.querySelector('.take');
  const prog = document.getElementById('prog');

  function render(t) {
    S.steps.forEach((s, i) => {
      const li = lis[i];
      const shown = seg(t, s.t0 - .25, s.t0 + .15);
      li.style.opacity = t < s.t0 - .25 ? .0 : (t >= s.t1 ? .55 : lerp(.0, 1, shown));
      li.style.transform = `translateY(${(1 - easeOut(shown)) * 10}px)`;
      li.classList.toggle('on', t >= s.t0 && t < s.t1);
    });
    const ta = seg(t, S.takeaway.t, S.takeaway.t + .4);
    take.style.opacity = ta;
    take.style.transform = `translateY(${(1 - easeOut(ta)) * 12}px)`;
    prog.style.width = (t / DUR * 100) + '%';
    S.update(t, ctx);
  }
  window.renderFrame = render;
  window.DUR = DUR;

  if (!/capture/.test(location.search)) {
    const t0 = performance.now();
    const loop = now => { render(((now - t0) / 1000) % DUR); requestAnimationFrame(loop); };
    requestAnimationFrame(loop);
  } else {
    render(0);
  }
})();
