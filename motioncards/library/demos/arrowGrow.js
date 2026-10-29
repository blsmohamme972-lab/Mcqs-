// Three heat-loss arrows growing outward from a body outline.
let A = [];
function setup(api) { api.el("ellipse", {cx: 320, cy: 290, rx: 60, ry: 140, fill: "#ffccbc", stroke: "#bf6a50", "stroke-width": 2}, api.svg);
  A = ["M300 220 C250 200 210 190 160 190", "M345 240 C390 220 420 215 470 220", "M310 380 C270 400 240 410 190 420"].map((d) => R.arrowGrow(api, api.svg, d, "#ef6c00", 6)); }
function render(t, api) { A.forEach((a, i) => a.update(t, api.seg(t, 200 + i * 600, 900 + i * 600, "ease_out"))); }
