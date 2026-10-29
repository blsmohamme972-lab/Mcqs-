import test from 'node:test';
import assert from 'node:assert/strict';
import { Channel, bezier, ease, easeFn, layoutTimeline, normWord, parseSentence, plainText, spokenText, syllables } from '../engine/core.js';

const near = (a, b, eps = 1e-6) => assert.ok(Math.abs(a - b) <= eps, `${a} != ${b}`);

test('every named easing starts at 0 and ends at 1', () => {
  for (const [name, f] of Object.entries(ease)) {
    near(f(0), 0, 1e-9);
    near(f(1), 1, 1e-6);
    assert.ok(Number.isFinite(f(0.5)), name);
  }
});

test('outSoft overshoots slightly and settles', () => {
  const peak = Math.max(...Array.from({ length: 201 }, (_, i) => ease.outSoft(i / 200)));
  assert.ok(peak > 1.03 && peak < 1.12, `peak ${peak}`);
});

test('bezier easing is monotonic for a standard curve and matches CSS "ease" at the midpoint', () => {
  const f = bezier(0.25, 0.1, 0.25, 1);
  let prev = 0;
  for (let i = 1; i <= 100; i++) { const v = f(i / 100); assert.ok(v >= prev - 1e-9); prev = v; }
  near(f(0.5), 0.8024, 2e-3);
});

test('easeFn accepts names, arrays and functions and rejects unknown names', () => {
  near(easeFn('linear')(0.3), 0.3);
  near(easeFn([0, 0, 1, 1])(0.3), 0.3, 1e-4);
  near(easeFn((t) => t * t)(0.5), 0.25);
  assert.throws(() => easeFn('nope'));
});

test('Channel: value at T does not depend on evaluation order', () => {
  const build = () => {
    const c = new Channel(0);
    c.to(2, 1, 100, { ease: 'inOutCubic' }).to(5, 2, 20, { ease: 'outExpo' }).to(1, 0.5, 40, { ease: 'linear' });
    return c;
  };
  const times = [0, 0.9, 1.2, 1.5, 2.4, 3, 5.7, 7, 9];
  const forward = build(), shuffled = build();
  const expected = times.map((t) => forward.at(t));
  const order = [6, 2, 8, 0, 5, 1, 7, 3, 4];
  const got = [];
  for (const i of order) got[i] = shuffled.at(times[i]);
  assert.deepEqual(got, expected);
});

test('Channel: segments chain from the previous value, explicit `from` wins, overlap is continuous', () => {
  const c = new Channel(5);
  c.to(1, 1, 15, { ease: 'linear' }); // 5 → 15
  c.to(3, 1, 0, { ease: 'linear', from: 100 }); // jumps to 100 then → 0
  near(c.at(0), 5); near(c.at(1.5), 10); near(c.at(2.5), 15); near(c.at(3), 100); near(c.at(3.5), 50); near(c.at(9), 0);

  const o = new Channel(0);
  o.to(0, 2, 10, { ease: 'linear' });
  o.to(1, 2, 0, { ease: 'linear' }); // starts while the first is at 5
  near(o.at(1), 5); near(o.at(2), 2.5); near(o.at(3), 0);
});

test('syllable heuristic is sane for clinical vocabulary', () => {
  const cases = { pain: 1, angina: 3, exertion: 3, nocturnal: 3, orthopnea: 3, cholesterol: 4, the: 1 };
  for (const [w, n] of Object.entries(cases)) assert.ok(Math.abs(syllables(w) - n) <= 1, `${w}: ${syllables(w)} vs ${n}`);
});

test('parseSentence splits phrases and applies shown=spoken overrides', () => {
  const p = parseSentence('Class {III=three} and {IV=four}, / carry more risk.');
  assert.equal(p.length, 2);
  assert.deepEqual(p[0].words.map((w) => w.shown), ['Class', 'III', 'and', 'IV,']);
  assert.deepEqual(p[0].words.map((w) => w.spoken), ['Class', 'three', 'and', 'four']);
  assert.equal(plainText('Class {III=three} and {IV=four}, / carry more risk.'), 'Class III and IV, carry more risk.');
  assert.equal(spokenText('Class {III=three} and {IV=four}, / carry more risk.'), 'Class three and four carry more risk.');
  assert.equal(normWord('IV,'), 'iv');
});

test('parseSentence keeps multi-word spoken overrides in one token', () => {
  const p = parseSentence('After a failed {PCI=P C I}, / the {COPD=C O P D} patient.');
  assert.deepEqual(p[0].words.map((w) => w.shown), ['After', 'a', 'failed', 'PCI,']);
  assert.equal(p[0].words[3].spoken, 'P C I');
  assert.equal(p[1].words.length, 3);
  assert.equal(spokenText('After a failed {PCI=P C I}, / the {COPD=C O P D} patient.'), 'After a failed P C I the C O P D patient.');
});

const script = {
  sentences: [
    { id: 'a', text: 'Angina is not always / a crushing pain.' },
    { id: 'b', text: 'Ask about precipitants: / exertion, stress, / emotion and cold air.' },
    { id: 'c', text: 'Grade it, because / class {III=three} and {IV=four} carry more risk.', pause: 0.6 },
  ],
};

test('layoutTimeline fills the reel and keeps words ordered and non-overlapping', () => {
  const t = layoutTimeline(script, { duration: 60 });
  near(t.meta.endsAt, 60 - t.tail, 1e-6);
  let prevEnd = 0;
  for (const s of t.sentences) {
    assert.ok(s.start >= prevEnd - 1e-9);
    let wEnd = s.start;
    for (const w of s.words) { assert.ok(w.start >= wEnd - 1e-9); assert.ok(w.end > w.start); wEnd = w.end; }
    near(s.words.at(-1).end, s.end, 1e-6);
    prevEnd = s.end;
  }
  assert.equal(t.sentences[1].phrases.length, 3);
});

test('layoutTimeline with real audio durations keeps them and only flexes gaps', () => {
  const dur = { a: 4.2, b: 6.1, c: 5.5 };
  const t = layoutTimeline(script, { duration: 30, audioDurations: dur });
  assert.equal(t.meta.usingAudio, true);
  for (const s of t.sentences) near(s.dur, dur[s.id], 1e-9);
  assert.ok(t.meta.endsAt <= 30 - t.tail + 1e-6);
  assert.throws(() => layoutTimeline(script, { duration: 12, audioDurations: dur }), /longer than/);
});
