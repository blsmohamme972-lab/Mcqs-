#!/usr/bin/env node
// Prints the computed timeline of a reel: node scripts/timeline.mjs <reel> [--words]
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { layoutTimeline } from '../engine/core.js';
import { ROOT, audioDurations } from './server.mjs';

const id = process.argv[2];
const words = process.argv.includes('--words');
const { script } = await import(pathToFileURL(path.join(ROOT, 'reels', id, 'script.js')).href);
const t = layoutTimeline(script, { duration: script.duration ?? 60, audioDurations: audioDurations(id) });
const f = (x) => x.toFixed(2).padStart(5);
console.log(`${id}: k=${t.meta.k?.toFixed(2)} ends ${f(t.meta.endsAt)} s`);
for (const s of t.sentences) {
  console.log(`${f(s.start)}–${f(s.end)}  ${s.id.padEnd(8)} ${s.words.map((w) => w.shown).join(' ')}`);
  if (words) console.log('            ' + s.words.map((w) => `${w.shown}@${w.start.toFixed(2)}`).join('  '));
}
