// Tiny static server for the reel stage: engine, reels, fonts, the icon set and computed timing.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { layoutTimeline } from '../engine/core.js';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.woff2': 'font/woff2', '.svg': 'image/svg+xml', '.png': 'image/png' };

let iconCache = null;
function icons() {
  if (iconCache) return iconCache;
  const dir = path.join(ROOT, 'node_modules/lucide-static/icons');
  iconCache = {};
  for (const f of fs.readdirSync(dir)) {
    if (!f.endsWith('.svg')) continue;
    const svg = fs.readFileSync(path.join(dir, f), 'utf8').replace(/<!--[\s\S]*?-->/g, '');
    const inner = svg.replace(/^[\s\S]*?<svg[^>]*>/, '').replace(/<\/svg>\s*$/, '').trim();
    iconCache[f.slice(0, -4)] = inner;
  }
  return iconCache;
}

/** Narration durations (seconds per sentence id) from audio/<reel>/durations.json, if audio exists. */
export function audioDurations(id) {
  const f = path.join(ROOT, 'audio', id, 'durations.json');
  return fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf8')) : null;
}

export async function timingFor(id) {
  const { script } = await import(pathToFileURL(path.join(ROOT, 'reels', id, 'reel.js')).href + `?t=${Date.now()}`);
  return layoutTimeline(script, { duration: script.duration ?? 60, audioDurations: audioDurations(id) });
}

export function startServer(port = 0) {
  const server = http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url, 'http://x');
      res.setHeader('Cache-Control', 'no-store');
      if (url.pathname === '/') { res.writeHead(302, { Location: '/engine/stage.html' + url.search }); return res.end(); }
      if (url.pathname === '/stage.html') { url.pathname = '/engine/stage.html'; }
      if (url.pathname === '/icons.json') { res.setHeader('Content-Type', MIME['.json']); return res.end(JSON.stringify(icons())); }
      const m = url.pathname.match(/^\/api\/timing\/([\w.-]+)$/);
      if (m) { res.setHeader('Content-Type', MIME['.json']); return res.end(JSON.stringify(await timingFor(m[1]))); }
      const file = path.join(ROOT, decodeURIComponent(url.pathname));
      if (!file.startsWith(ROOT + path.sep) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end('not found'); }
      res.setHeader('Content-Type', MIME[path.extname(file)] ?? 'application/octet-stream');
      fs.createReadStream(file).pipe(res);
    } catch (e) {
      res.writeHead(500, { 'Content-Type': 'text/plain' });
      res.end(String(e.stack || e));
    }
  });
  return new Promise((resolve) => server.listen(port, '127.0.0.1', () => resolve({ server, port: server.address().port })));
}
