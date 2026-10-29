#!/usr/bin/env node
// Render a reel with headless Chromium (deterministic frame-by-frame) and encode it with ffmpeg.
//
//   node scripts/render.mjs <reel-id>                       → out/<reel-id>/<reel-id>.mp4  (1080×1920, 30 fps, exact duration)
//   node scripts/render.mjs <reel-id> --stills 2,8.5,30      → PNGs in out/<reel-id>/stills (+ --sheet sheet.png)
//   node scripts/render.mjs <reel-id> --audit                → layout audit (out of bounds / clipped / overlapping text)
//   options: --fps 30  --crf 21  --preset slow  --scale 1  --audio <file>  --out <file>
import { createRequire } from 'node:module';
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { once } from 'node:events';
import { startServer, ROOT } from './server.mjs';

const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); } catch {
  console.error('playwright is not installed. Run: npm i -g playwright && npx playwright install chromium');
  process.exit(1);
}

const argv = process.argv.slice(2);
const id = argv.find((a) => !a.startsWith('--'));
const opt = (name, def) => { const i = argv.indexOf(`--${name}`); return i < 0 ? def : (argv[i + 1]?.startsWith('--') || i + 1 >= argv.length ? true : argv[i + 1]); };
if (!id) { console.error('usage: render.mjs <reel-id> [--stills t,t] [--audit] [--out file]'); process.exit(1); }

const fps = +opt('fps', 30), crf = +opt('crf', 21), preset = opt('preset', 'slow'), scale = +opt('scale', 1);
const outDir = path.join(ROOT, 'out', id);
fs.mkdirSync(outDir, { recursive: true });

const { server, port } = await startServer();
const browser = await chromium.launch({ args: ['--force-color-profile=srgb', '--font-render-hinting=none', '--disable-lcd-text', '--hide-scrollbars'] });
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: scale });
page.on('console', (m) => { if (['error', 'warning'].includes(m.type())) console.error(`[page ${m.type()}]`, m.text()); });
page.on('pageerror', (e) => console.error('[pageerror]', e.message));
await page.goto(`http://127.0.0.1:${port}/engine/stage.html?reel=${id}`);
await page.waitForFunction(() => window.__ready || window.__error, null, { timeout: 60000 });
const fatal = await page.evaluate(() => window.__error);
if (fatal) { console.error(fatal); await browser.close(); server.close(); process.exit(1); }
const duration = await page.evaluate(() => window.__duration);
const seek = (t) => page.evaluate((x) => window.__seek(x), t);

async function finish(code = 0) { await browser.close(); server.close(); process.exit(code); }

if (opt('audit', false)) {
  const times = [];
  for (let t = 0.2; t < duration; t += 0.5) times.push(+t.toFixed(2));
  const issues = await page.evaluate((ts) => window.__audit(ts), times);
  const seen = new Map();
  for (const i of issues) { const k = `${i.kind}|${i.what}`; (seen.get(k) ?? seen.set(k, []).get(k)).push(i); }
  for (const [k, list] of seen) console.log(`${list[0].kind.toUpperCase().padEnd(8)} ${list[0].what}  t=${list.map((i) => i.t).slice(0, 6).join(',')}${list.length > 6 ? '…' : ''}${list[0].rect ? '  rect=' + list[0].rect : ''}${list[0].frac ? '  frac=' + list[0].frac : ''}`);
  console.log(`audit: ${seen.size} distinct issue(s) over ${times.length} samples`);
  await finish(seen.size ? 2 : 0);
}

if (opt('stills', false)) {
  const times = String(opt('stills')).split(',').map(Number);
  const dir = path.join(outDir, 'stills');
  fs.mkdirSync(dir, { recursive: true });
  const files = [];
  for (const t of times) {
    await seek(t);
    const f = path.join(dir, `t${t.toFixed(2).padStart(6, '0')}.png`);
    await page.screenshot({ path: f });
    files.push(f);
  }
  console.log(files.join('\n'));
  const sheet = opt('sheet', false);
  if (sheet) {
    const r = spawnSync('python3', ['-I', path.join(ROOT, 'scripts/contact.py'), path.resolve(sheet === true ? path.join(outDir, 'sheet.png') : sheet), ...files], { stdio: 'inherit' });
    if (r.status) console.error('contact sheet failed');
  }
  await finish();
}

// ---------------------------------------------------------------------------------------- video
const out = path.resolve(opt('out', path.join(outDir, `${id}.mp4`)));
const audio = opt('audio', false);
const frames = Math.round(duration * fps);
const ff = spawn('ffmpeg', [
  '-y', '-loglevel', 'error', '-f', 'image2pipe', '-vcodec', 'mjpeg', '-framerate', String(fps), '-i', 'pipe:0',
  ...(audio ? ['-i', path.resolve(audio)] : []),
  // JPEG frames are full-range BT.601 YCbCr; convert to the BT.709 limited range every phone expects.
  '-vf', 'scale=in_range=pc:in_color_matrix=bt601:out_range=tv:out_color_matrix=bt709:flags=accurate_rnd+full_chroma_int,format=yuv420p',
  '-c:v', 'libx264', '-preset', String(preset), '-crf', String(crf), '-tune', 'animation', '-profile:v', 'high', '-level', '4.2',
  '-x264-params', 'aq-mode=3:deblock=1,1', '-g', String(fps * 2), '-bf', '2',
  '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
  ...(audio ? ['-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-ac', '2', '-af', `apad,atrim=0:${duration}`] : ['-an']),
  '-t', String(duration), '-movflags', '+faststart', out,
], { stdio: ['pipe', 'inherit', 'inherit'] });
const ffDone = once(ff, 'close');

const cdp = await page.context().newCDPSession(page);
const t0 = Date.now();
for (let i = 0; i < frames; i++) {
  await seek(i / fps);
  const { data } = await cdp.send('Page.captureScreenshot', { format: 'jpeg', quality: 96, optimizeForSpeed: true });
  if (!ff.stdin.write(Buffer.from(data, 'base64'))) await once(ff.stdin, 'drain');
  if (i % 150 === 149 || i === frames - 1) {
    const el = (Date.now() - t0) / 1000;
    process.stdout.write(`\r${id}: ${i + 1}/${frames} frames  ${(el / (i + 1) * (frames - i - 1)).toFixed(0)} s left   `);
  }
}
ff.stdin.end();
const [code] = await ffDone;
process.stdout.write('\n');
if (code) { console.error('ffmpeg failed'); await finish(1); }
const mb = (fs.statSync(out).size / 1048576).toFixed(1);
console.log(`wrote ${out}  (${duration}s, ${frames} frames, ${mb} MB)`);
await finish();
