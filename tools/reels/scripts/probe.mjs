#!/usr/bin/env node
// Debug helper: node scripts/probe.mjs <reel> <time> "<js expression>"   (the expression can use R = reel, Ws = worlds)
import { createRequire } from 'node:module';
import { startServer } from './server.mjs';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const [id, t, expr] = process.argv.slice(2);
const { server, port } = await startServer();
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
page.on('pageerror', (e) => console.error('[pageerror]', e.message));
await page.goto(`http://127.0.0.1:${port}/engine/stage.html?reel=${id}`);
await page.waitForFunction(() => window.__ready || window.__error, null, { timeout: 60000 });
const out = await page.evaluate(([t, expr]) => { window.__seek(+t); const R = window.__reel, Ws = globalThis.__worlds; return JSON.stringify(eval(expr), null, 1); }, [t, expr]);
console.log(out);
await browser.close(); server.close();
