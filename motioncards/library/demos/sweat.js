// Droplets beading up on a surface, then drying.
let sw;
function setup(api) { api.el("rect", {x: 170, y: 200, width: 300, height: 160, rx: 30, fill: "#f6d5c8"}, api.svg);
  sw = R.sweat(api, api.svg, [[220, 250, 1.3], [290, 300, 1.5], [360, 240, 1.2], [420, 310, 1.4], [250, 330, 1.1], [400, 260, 1.0]]); }
function render(t, api) { sw.update(t, api.seg(t, 200, 1800) * (1 - api.seg(t, 2300, 2900))); }
