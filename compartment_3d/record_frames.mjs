// Record the 3D layer of the lesson frame by frame (layer 1 for ffmpeg/compose.sh).
//
// Opens compartment_3d.html#clean (no chart, no captions: Manim and libass add those),
// seeks to each frame time with window.__seek(t), and screenshots the stage as JPEG.
// Deterministic: every frame is computed from t, so a slow machine gives the same video.
//
// Usage: node record_frames.mjs 16x9|9x16 <frames dir> [fps=30]
// Needs: npm i playwright; CHROME=<path to chromium or headless_shell>
// No GPU needed (SwiftShader), but on a 4-core CPU 1080p takes ~5 s per frame.
import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const [, , orient = '16x9', outDir = 'frames', fps = '30'] = process.argv;
const here = path.dirname(fileURLToPath(import.meta.url));
// stage is 1120 px wide on desktop and 9:16 below 640 px; scale it to exactly 1080p
const view = orient === '9x16'
  ? { viewport: { width: 390, height: 900 }, deviceScaleFactor: 1080 / 358 }
  : { viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1920 / 1120 };

const browser = await chromium.launch({
  executablePath: process.env.CHROME,
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
});
const page = await browser.newPage(view);
await page.goto('file://' + path.join(here, 'compartment_3d.html') + '#clean');
await page.waitForFunction(() => typeof window.__seek === 'function', null, { timeout: 120000 });
const stage = page.locator('#stage');
const n = 30 * Number(fps);
for (let i = 0; i < n; i++) {
  await page.evaluate((s) => window.__seek(s), i / Number(fps));
  await stage.screenshot({ path: `${outDir}/f${String(i).padStart(4, '0')}.jpg`, type: 'jpeg', quality: 95 });
}
await browser.close();
