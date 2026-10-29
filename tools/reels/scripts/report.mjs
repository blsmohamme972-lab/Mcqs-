#!/usr/bin/env node
// Pacing report for every reel script, or a markdown export of the narration (--md) for fact-checking.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { layoutTimeline, parseSentence, plainText, spokenText } from '../engine/core.js';
import { ROOT } from './server.mjs';

const md = process.argv.includes('--md');
const dirs = fs.readdirSync(path.join(ROOT, 'reels')).filter((d) => d.startsWith('ch') && fs.existsSync(path.join(ROOT, 'reels', d, 'script.js'))).sort();
let bad = 0;
for (const d of dirs) {
  const { script } = await import(pathToFileURL(path.join(ROOT, 'reels', d, 'script.js')).href);
  const t = layoutTimeline(script, { duration: script.duration ?? 60 });
  const words = t.meta.words;
  const longest = Math.max(...script.sentences.flatMap((s) => parseSentence(s.text).map((p) => p.words.length)));
  if (md) {
    console.log(`\n## Reel ${String(script.index).padStart(2, '0')} · ${script.title}  (${script.source})`);
    for (const s of script.sentences) console.log(`- **${s.id}**: ${plainText(s.text)}`);
    continue;
  }
  const wps = words / t.meta.speechSeconds;
  const flag = t.meta.k < 0.85 ? 'TOO FAST' : t.meta.k > 1.3 ? 'TOO SLOW' : longest > 8 ? 'LONG PHRASE' : '';
  if (flag) bad++;
  console.log(`${String(script.index).padStart(2)} ${d.padEnd(30)} ${String(words).padStart(3)} words  ${t.meta.speechSeconds.toFixed(1).padStart(5)} s speech  k=${t.meta.k.toFixed(2)}  ${wps.toFixed(2)} w/s  longest phrase ${longest}  ${flag}`);
}
if (!md) console.log(bad ? `\n${bad} script(s) need attention` : '\nall scripts within pacing limits');
