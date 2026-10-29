// @recipes v1 begin - Kafu MotionCards animation recipes (tested; see AUTHORING_V2.md "Recipes").
// Build in setup(api), animate in render(t, api). Every recipe is a pure function of t, so pause and seek work.
// Coordinates are stage pixels. Shapes use the style kit (run `motioncards.py style-kit` on the scene).
const R = {
  FONT: "system-ui,sans-serif",
  // Parent for new elements: above imported art when given its id (e.g. R.layer(api, "#st")), else the stage.
  layer(api, id) { const a = id ? api.$(id) : null; return a ? a.parentNode : api.svg; },
  behind(el, ref) { ref.parentNode.insertBefore(el, ref); return el; },
  // Wrap imported art so it can be moved/faded without touching its own transform.
  wrap(api, el) { const g = api.el("g", {}, el.parentNode); el.parentNode.insertBefore(g, el); g.appendChild(el); return g; },
  // Opacity schedule: fade in over [a,b], optionally out over [c,d]. Accepts one element or an array.
  fade(api, els, t, a, b, c, d) { const o = api.seg(t, a, b) * (c ? 1 - api.seg(t, c, d) : 1); [].concat(els).forEach((e) => e && api.set(e, {opacity: o})); return o; },
  // Scale an element about a point (default: its own centre at creation).
  scaleAbout(api, el, s, c) { let p = c || el._c; if (!p) { const b = el.getBBox(); p = el._c = [b.x + b.width / 2, b.y + b.height / 2]; }
    api.set(el, {transform: `translate(${p[0]} ${p[1]}) scale(${(+s).toFixed(3)}) translate(${-p[0]} ${-p[1]})`}); },
  // ---- Labels ----
  text(api, g, txt, x, y, o) { o = o || {}; const sz = o.size || 16;
    const t = api.el("text", {x, y, "text-anchor": o.anchor || "start", "font-size": sz, "font-weight": o.weight || 800, fill: o.color || "#16323a", stroke: o.halo === false ? "none" : "#fff", "stroke-width": 4, "paint-order": "stroke", "font-family": R.FONT}, g);
    String(txt).split("\n").forEach((ln, i) => { const s = api.el("tspan", {x, dy: i ? sz * 1.2 : 0}, t); s.textContent = ln; }); return t; },
  // White label card with a coloured edge and soft shadow. Returns the group (fade it with R.fade).
  chip(api, g, txt, x, y, color, o) { o = o || {};
    const grp = api.el("g", {filter: "url(#kit-shadow)"}, g), t = R.text(api, grp, txt, x, y, {color, size: o.size || 15, anchor: o.anchor, halo: false});
    const b = t.getBBox(), pad = 8;
    grp.insertBefore(api.el("rect", {x: b.x - pad, y: b.y - pad + 2, width: b.width + 2 * pad, height: b.height + 2 * pad - 3, rx: 10, fill: "#fff"}, grp), t);
    grp.insertBefore(api.el("rect", {x: b.x - pad, y: b.y - pad + 2, width: 4, height: b.height + 2 * pad - 3, rx: 2, fill: color}, grp), t);
    grp.setAttribute("opacity", 0); return grp; },
  // Leader line ending in a dot on the structure.
  leader(api, g, x1, y1, x2, y2, color) { const grp = api.el("g", {opacity: 0}, g);
    api.el("path", {d: `M${x1} ${y1}L${x2} ${y2}`, stroke: color, "stroke-width": 2, fill: "none", "stroke-linecap": "round"}, grp);
    api.el("circle", {cx: x2, cy: y2, r: 3.5, fill: color, stroke: "#fff", "stroke-width": 1.5}, grp); return grp; },
  // Chip + leader in one call; returns [chip, leader] for R.fade.
  callout(api, g, txt, x, y, color, to, from) { const c = R.chip(api, g, txt, x, y, color);
    if (!to) return [c]; const b = c.getBBox(), f = from || [b.x + b.width / 2, b.y + b.height / 2];
    const l = R.leader(api, g, f[0], f[1], to[0], to[1], color); g.insertBefore(l, c); return [c, l]; },
  // ---- Tubes: vessels, nerves, ducts ----
  // kind: artery | vein | nerve | bile | gut. Returns a group; .p is the centre path for pointAt/flow.
  tube(api, g, d, kind, w, o) { o = o || {}; w = w || 8;
    const K = {artery: ["#7d1a20", "url(#kit-artery)"], vein: ["#1f3a6e", "url(#kit-vein)"], nerve: ["#7a5a00", "url(#kit-nerve)"], bile: ["#2d5a1c", "#6fae4a"], gut: ["#b5616b", "#eab0aa"]}[kind] || ["#555", "#aaa"];
    const grp = api.el("g", {}, g);
    api.el("path", {d, fill: "none", stroke: K[0], "stroke-width": w + 3, "stroke-linecap": "round", "stroke-linejoin": "round"}, grp);
    grp.p = api.el("path", {d, fill: "none", stroke: K[1], "stroke-width": w, "stroke-linecap": "round", "stroke-linejoin": "round"}, grp);
    grp.fill = K[1]; if (o.behind) R.behind(grp, o.behind); return grp; },
  // Draw a tube (or any path group) on progressively: f in 0..1.
  drawOn(api, grp, f) { (grp.tagName === "path" ? [grp] : Array.from(grp.querySelectorAll("path"))).forEach((p) => {
    const L = p.getTotalLength(); api.set(p, {"stroke-dasharray": `${L.toFixed(1)} ${L.toFixed(1)}`, "stroke-dashoffset": (L * (1 - f)).toFixed(1)}); }); },
  // Narrow (or widen) a tube: width w at progress f between w0 and w1.
  squeeze(api, grp, f, w0, w1) { const w = w0 + (w1 - w0) * f, ps = grp.querySelectorAll("path");
    api.set(ps[0], {"stroke-width": (w + 3).toFixed(2)}); api.set(ps[1], {"stroke-width": w.toFixed(2)}); },
  // ---- Moving things ----
  // Particles flowing along a path (blood, bile, air, food). Call .update(t, on) every frame.
  flow(api, g, path, o) { o = o || {}; const n = o.n || 6, period = o.period || 1300;
    const dots = Array.from({length: n}, () => api.el("circle", {r: o.r || 3, fill: o.color || "#ffe0e0", opacity: 0}, g));
    if (o.behind) dots.forEach((d) => R.behind(d, o.behind));
    return {dots, update(t, on) { on = on === undefined ? 1 : on; dots.forEach((c, i) => { let f = ((t / period) + i / n) % 1; if (o.reverse) f = 1 - f;
      const q = api.pointAt(path, (o.from || 0) + f * ((o.to === undefined ? 1 : o.to) - (o.from || 0)));
      api.set(c, {cx: q.x.toFixed(1), cy: q.y.toFixed(1), opacity: (on * Math.sin(f * Math.PI)).toFixed(3)}); }); }};
  },
  // Glowing impulses travelling along a nerve (reverse: toward the path start).
  impulses(api, g, path, o) { o = o || {}; const n = o.n || 3, period = o.period || 1000;
    const dots = Array.from({length: n}, () => api.el("circle", {r: o.r || 6, fill: "#fffbe6", stroke: o.color || "#ffb300", "stroke-width": 2, filter: "url(#kit-glow)", opacity: 0}, g));
    return {dots, update(t, on) { on = on === undefined ? 1 : on; dots.forEach((c, i) => { const f = ((t / period) + i / n) % 1, q = api.pointAt(path, o.reverse ? 1 - f : f);
      api.set(c, {cx: q.x.toFixed(1), cy: q.y.toFixed(1), opacity: (on * Math.sin(f * Math.PI)).toFixed(3)}); }); }};
  },
  // Pulsatile arterial bleeding from a point: bursts in a fan around `angle` (radians, 0 = right, -PI/2 = up).
  bleed(api, g, x, y, o) { o = o || {}; const n = o.n || 10, period = o.period || 600, spread = o.spread || 2.2, reach = o.reach || 60, a0 = o.angle === undefined ? -Math.PI / 2 : o.angle;
    const dots = Array.from({length: n}, () => api.el("circle", {r: o.r || 4, fill: o.color || "#c62828", opacity: 0}, g));
    const ring = api.el("circle", {cx: x, cy: y, r: o.ring || 22, fill: "none", stroke: "#e53935", "stroke-width": 4, opacity: 0}, g);
    return {dots, ring, update(t, on) { on = on === undefined ? 1 : on; const beat = Math.max(0, Math.sin(t / 95));
      api.set(ring, {opacity: (on * (0.4 + 0.6 * beat)).toFixed(3)});
      dots.forEach((d, i) => { const f = ((t / period) + i / n) % 1, a = a0 - spread / 2 + spread * i / Math.max(1, n - 1);
        api.set(d, {cx: (x + Math.cos(a) * reach * f).toFixed(1), cy: (y + Math.sin(a) * reach * f + (o.gravity || 0) * f * f).toFixed(1), opacity: (on * (1 - f)).toFixed(3)}); }); }};
  },
  // Dripping (venous/ooze) bleeding falling from a point.
  drip(api, g, x, y, o) { o = o || {}; const n = o.n || 8, period = o.period || 900, fall = o.fall || 110;
    const dots = Array.from({length: n}, () => api.el("circle", {r: o.r || 4.5, fill: o.color || "#c62828", opacity: 0}, g));
    return {dots, update(t, on) { on = on === undefined ? 1 : on; dots.forEach((d, i) => { const f = ((t / period) + i / n) % 1;
      api.set(d, {cx: x + ((i % 3) - 1) * 7, cy: (y + f * fall).toFixed(1), opacity: (on * (1 - f)).toFixed(3)}); }); }};
  },
  // A lump (tumour, cyst, mass, aneurysm) that grows. kind: tumour | cyst | mass | artery.
  lump(api, g, cx, cy, kind, o) { o = o || {};
    const fills = {tumour: ["url(#kit-tumour)", "#4b2a5c"], cyst: ["url(#kit-cyst)", "#2f6a99"], mass: ["url(#kit-mass)", "#7a6a58"], artery: ["url(#kit-artery)", "#7d1a20"]}[kind] || ["url(#kit-tissue)", "#b5616b"];
    R._extraFills(api);
    const el = api.el("ellipse", {cx, cy, rx: 1, ry: 1, fill: fills[0], stroke: fills[1], "stroke-width": 2, filter: "url(#kit-volume)", opacity: 0}, g);
    if (o.behind) R.behind(el, o.behind);
    return {el, update(t, f, rx, ry, pulse) { const p = pulse ? 1 + 0.03 * Math.sin(t / 130) * f : 1;
      api.set(el, {rx: (1 + (rx - 1) * f) * p, ry: (1 + ((ry || rx) - 1) * f) * p, opacity: f > 0 ? 1 : 0}); }};
  },
  _extraFills(api) { if (api.$("#kit-cyst")) return; const kit = api.$("#kit") || api.el("defs", {id: "kit"}, api.svg);
    [["kit-cyst", [[0, "#f2fbff"], [0.6, "#a9d3ee"], [1, "#5d9cc9"]]], ["kit-mass", [[0, "#f4efe8"], [0.6, "#cdbfae"], [1, "#9a8672"]]], ["kit-blood", [[0, "#d32f2f"], [1, "#7f0000"]]]].forEach(([id, stops]) => {
      const gr = api.el("radialGradient", {id, cx: 0.38, cy: 0.32, r: 0.8}, kit); stops.forEach(([o, c]) => api.el("stop", {offset: o, "stop-color": c}, gr)); }); },
  // Crater (ulcer) that deepens: f in 0..1.
  ulcer(api, g, cx, cy, o) { o = o || {}; const el = api.el("ellipse", {cx, cy, rx: 1, ry: 1, fill: "#5e0d12", stroke: "#c2484a", "stroke-width": 3, filter: "url(#kit-volume-sm)", opacity: 0}, g);
    return {el, update(t, f) { api.set(el, {rx: (1 + ((o.rx || 16) - 1) * f).toFixed(1), ry: (1 + ((o.ry || 11) - 1) * f).toFixed(1), opacity: f > 0 ? 1 : 0}); }};
  },
  // Pulsing glow (pain, inflammation, danger).
  glow(api, g, cx, cy, o) { o = o || {}; const el = api.el("circle", {cx, cy, r: o.r || 18, fill: o.color || "#e53935", opacity: 0, filter: "url(#kit-glow)"}, g);
    if (o.behind) R.behind(el, o.behind);
    return {el, update(t, on) { const p = 0.5 + 0.5 * Math.sin(t / (o.speed || 140)); api.set(el, {opacity: (on * (0.4 + 0.4 * p)).toFixed(3), r: ((o.r || 18) * (0.9 + 0.2 * p)).toFixed(1)}); }};
  },
  // A sac/bolus/catheter travelling along a route, drawn on behind its rounded head. f in 0..1.
  travel(api, g, d, o) { o = o || {}; const w = o.width || 24;
    const route = api.el("path", {d, fill: "none", stroke: "none"}, g);
    const edge = api.el("path", {d, fill: "none", stroke: o.edge || "#b5616b", "stroke-width": w + 5, "stroke-linecap": "round", opacity: 0}, g);
    const body = api.el("path", {d, fill: "none", stroke: o.color || "#f2b3b5", "stroke-width": w, "stroke-linecap": "round", opacity: 0}, g);
    const head = api.el("circle", {r: w * 0.62, fill: "url(#kit-tissue)", stroke: o.edge || "#b5616b", "stroke-width": 2.5, filter: "url(#kit-volume-sm)", opacity: 0}, g);
    const L = route.getTotalLength();
    return {route, update(t, f) { const len = Math.max(0.1, L * f); [edge, body].forEach((p) => api.set(p, {"stroke-dasharray": `${len.toFixed(1)} ${(L + 40).toFixed(1)}`, opacity: f > 0 ? 1 : 0}));
      const q = api.pointAt(route, f); api.set(head, {cx: q.x.toFixed(1), cy: q.y.toFixed(1), opacity: f > 0 ? 1 : 0}); }};
  },
  // Make imported art see-through (to reveal what lies behind it): f in 0..1 -> opacity 1..min.
  seeThrough(api, el, f, min) { api.set(el, {opacity: (1 - (1 - (min === undefined ? 0.45 : min)) * f).toFixed(3)}); },
  // Debug only: a 20 px grid with labels, to read where imported art landed. Remove before packaging.
  grid(api) { for (let x = 0; x <= api.W; x += 20) api.el("path", {d: `M${x} 0V${api.H}`, stroke: x % 100 ? "#0a0" : "#f00", "stroke-width": x % 100 ? 0.3 : 0.8}, api.svg);
    for (let y = 0; y <= api.H; y += 20) api.el("path", {d: `M0 ${y}H${api.W}`, stroke: y % 100 ? "#0a0" : "#f00", "stroke-width": y % 100 ? 0.3 : 0.8}, api.svg); },
  // ---- Temperature, sweat, arrows (added with the temperature-regulation cards) ----
  // Vertical thermometer: tube top at y0, bulb at y1, scale lo..hi °C with optional ticks. .update(v, color) every frame.
  thermometer(api, g, x, y0, y1, lo, hi, o) { o = o || {}; const grp = api.el("g", {}, g), Y = (v) => y1 - (v - lo) / (hi - lo) * (y1 - y0);
    api.el("rect", {x: x - 10, y: y0 - 10, width: 20, height: y1 - y0 + 12, rx: 10, fill: "#fff", stroke: "#8aa0ad", "stroke-width": 2}, grp);
    api.el("circle", {cx: x, cy: y1 + 10, r: 16, fill: "#fff", stroke: "#8aa0ad", "stroke-width": 2}, grp);
    const col = api.el("rect", {x: x - 5, y: y1, width: 10, height: 1, rx: 5, fill: "#e53935"}, grp), bulb = api.el("circle", {cx: x, cy: y1 + 10, r: 11, fill: "#e53935"}, grp);
    (o.ticks || []).forEach((v) => { api.el("path", {d: `M${x + 11} ${Y(v)}h7`, stroke: "#8aa0ad", "stroke-width": 2}, grp); R.text(api, grp, v + "°", x + 21, Y(v) + 5, {size: 13, color: "#58707c", weight: 700}); });
    const lab = o.label === false ? null : R.text(api, grp, "", x, y1 + 50, {anchor: "middle", size: 19});
    return {g: grp, Y, update(v, c) { c = c || "#e53935"; const yy = Y(Math.max(lo, Math.min(hi, v))); api.set(col, {y: yy, height: y1 - yy + 6, fill: c}); api.set(bulb, {fill: c});
      if (lab) { lab.textContent = v.toFixed(o.decimals || 0) + "°C"; api.set(lab, {fill: c}); } }};
  },
  // Sweat (or any liquid) droplets at points [[x, y, size], ...] that bead up one after another. .update(t, f): f 0..1 = how wet.
  sweat(api, g, pts, o) { o = o || {}; const drops = pts.map(([x, y, s]) => { s = s || 1; const d = api.el("g", {opacity: 0}, g);
      api.el("path", {d: `M${x} ${y - 9 * s}C${x + 6 * s} ${y - 2 * s} ${x + 6 * s} ${y + 6 * s} ${x} ${y + 6 * s}C${x - 6 * s} ${y + 6 * s} ${x - 6 * s} ${y - 2 * s} ${x} ${y - 9 * s}Z`, fill: o.color || "#7cc4f0", stroke: o.edge || "#2b7bb9", "stroke-width": 1.2}, d);
      api.el("circle", {cx: x - 2 * s, cy: y + s, r: 1.6 * s, fill: "#fff", opacity: 0.85}, d); return d; });
    return {drops, update(t, f) { drops.forEach((d, i) => { const on = Math.max(0, Math.min(1, (f * drops.length - i * 0.75) / 2));
      api.set(d, {opacity: on.toFixed(3)}); R.scaleAbout(api, d, 0.4 + 0.6 * on + 0.05 * Math.sin(t / 300 + i)); }); }};
  },
  // Arrow along any path d that grows from its start: f 0..1. For heat loss, flow direction, cause -> effect.
  arrowGrow(api, g, d, color, w) { w = w || 5; const grp = api.el("g", {opacity: 0}, g);
    const p = api.el("path", {d, fill: "none", stroke: color || "#ef6c00", "stroke-width": w, "stroke-linecap": "round"}, grp), L = p.getTotalLength();
    const head = api.el("path", {d: `M0 0L${-w * 2.6} ${-w * 1.3}L${-w * 2.6} ${w * 1.3}Z`, fill: color || "#ef6c00"}, grp);
    return {g: grp, update(t, f) { f = Math.max(0, Math.min(1, f)); api.set(grp, {opacity: f > 0 ? 1 : 0}); api.set(p, {"stroke-dasharray": `${(L * f).toFixed(1)} ${(L + 10).toFixed(1)}`});
      const q = api.pointAt(p, Math.max(0.001, f)); api.set(head, {transform: `translate(${q.x.toFixed(1)} ${q.y.toFixed(1)}) rotate(${q.angle.toFixed(1)})`}); }};
  },
};
// @recipes v1 end
