// Core temperature falling from 37 to 34 °C, crossing the 35 °C hypothermia line.
let th;
function setup(api) { th = R.thermometer(api, api.svg, 320, 140, 380, 31, 38, {ticks: [32, 34, 35, 36, 37]}); }
function render(t, api) { const f = api.seg(t, 300, 2600); th.update(37 - 3 * f, api.mixColor("#e53935", "#1e88e5", f)); }
