// Page entry: loads a reel module, its timing and the icon set, builds the scene and exposes
// window.__seek(t) / window.__audit(times) for the renderer.
import { Reel, audit } from './dom.js';

const FONTS = ['400 100px "Instrument Serif"', 'italic 400 100px "Instrument Serif"', '500 40px Inter', '600 40px Inter', '700 40px Inter', '800 40px Inter', '500 24px "JetBrains Mono"', '700 24px "JetBrains Mono"'];

async function main() {
  const id = new URLSearchParams(location.search).get('reel');
  if (!id) throw new Error('missing ?reel=<id>');
  const [mod, timing, icons] = await Promise.all([
    import(`/reels/${id}/reel.js`),
    fetch(`/api/timing/${id}`).then((r) => (r.ok ? r.json() : Promise.reject(new Error(`timing: ${r.status}`)))),
    fetch('/icons.json').then((r) => r.json()),
  ]);
  await Promise.all(FONTS.map((f) => document.fonts.load(f)));
  await Promise.all(['500', '600', '700', '800'].map((w) => document.fonts.load(`${w} 40px Inter`, 'βαμ°≥'))); // Greek letters (β-blockers)
  await document.fonts.ready;

  const R = new Reel({ stage: document.getElementById('stage'), timing, icons, meta: mod.script });
  R.background();
  R.hud(mod.script);
  mod.build(R);
  R.captions();
  R.render(0);

  window.__reel = R;
  window.__seek = (t) => R.render(t);
  window.__audit = (times, opts) => audit(R, times, { ...(mod.audit ?? {}), ...opts }); // a reel may `export const audit = { fade: false }` (scrolling charts)
  window.__duration = timing.duration;
  window.__ready = true;
}

main().catch((e) => { window.__error = String(e.stack || e); console.error(e); });
