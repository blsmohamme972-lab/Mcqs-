# Reel engine

Deterministic, code-drawn explainer reels for the study app. A reel is HTML/SVG rendered by headless Chromium, one frame at
a time, as a **pure function of time** (`render(T)`), then encoded with ffmpeg. Same input, same pixels; frames can be
rendered in any order or in parallel.

```
node scripts/timeline.mjs <reel> [--words]                    sentence / word timings for a script
node scripts/render.mjs <reel> --audit                        layout audit (bounds, clipped, overlap, fade zone) at 120 sample times
node scripts/render.mjs <reel> --stills 3,7.5,12 --sheet out/<reel>/sheet.png    PNG stills + contact sheet
node scripts/render.mjs <reel>                                full render → out/<reel>/<reel>.mp4  (1080×1920, 30 fps, 60.000 s)
node scripts/report.mjs                                       pacing report for all scripts
node scripts/probe.mjs <reel> <t> "<js>"                       evaluate JS in the page at time t (R = reel, Ws = worlds), for debugging
node --test                                                   unit tests (easing, channels, parser, timing, layout)
```

A reel lives in `reels/<id>/`: `script.js` (narration, metadata; **do not change the wording**) and `reel.js`
(`export { script }` + `export function build(R)`).

## Narration timing and cues

`script.sentences[i].text` uses `/` to split caption phrases and `{shown=spoken}` for words whose spoken form differs
(`{PCI=P C I}`). `layoutTimeline` spreads the sentences over 60 s (lead 0.6 s, tail 2 s) from a syllable estimate; when
`audio/<id>/durations.json` exists (real TTS) the same cues snap to the real durations. So **always cue animation from
words, never from hard-coded seconds**:

```js
const at = (sentenceId, word, n = 1) => R.s[sentenceId].at(word, n);   // start of the n-th occurrence
R.s.hook.at('black-out')       // keys are normalised: lower-case, punctuation / hyphens removed → 'blackout'
R.s.rec.at('what', 2)          // second "what"
R.s.drugs.at('causing')        R.s.x.endOf('urine')   R.s.x.start / .end / .frac(0.5)
```

A missing cue throws (with the sentence text), so typos are caught at once.

## World: maps and flow charts (`engine/world.js`)

A `World` is a big canvas seen through a viewport (y 180–1400, with a soft fade at both ends) with a camera that flies to
whatever the narrator is talking about.

```js
R.scene(0, 54, (sc) => {
  const W = new World(R, sc, { size: [1080, 5000] });          // world size in px
  const a = W.node('a', { kind: 'step', icon: 'zap', label: 'What brings it on?', sub: '…', tone: 'teal', num: 2, w: 700, x: 540, y: 400 });
  const kids = W.outline('a', [{ id: 'k1', icon: 'footprints', label: 'Exertion' }, …], { tone: 'teal', x: 180, gap: 18 }); // {nodes, edges, bottom}
  const z = W.zone(['a', 'k1', …], { tone: 'teal', label: 'Precipitants', extra: [rect] });   // district behind a cluster
  W.start(a);                                                        // camera at t = 0
  W.go(t - 0.45, 'a', { fit: z, max: 1.5, pad: 44, dur: 1.3 });      // fly there, fit the zone, fade whatever is left behind
  z.in(t - 0.3);
  W.appear(a, edgeIn, t, { hold: 99 });                              // reveal node (+ edge) at t, flash, then settle
  W.appear(kids.nodes[0], kids.edges[0], R.s.x.at('exertion') - 0.1, { hold: 1.2 });
  W.finish();                                                        // last line of build: districts grow with their content
}, { drift: 0, exit: { y: 0 } });
```

* **Node kinds** `step` (icon tile + label + sub) · `start` (big serif) · `chip` · `tag` · `decision` (hexagon) · `end`
  (filled pill) · `note` · `title`. `cls: 'sm'` shrinks chips; `num` adds a numbered badge; `w` fixes the width.
  Measure-then-place: nodes are measured from the DOM, so `n.w`, `n.h`, `n.box`, `n.port('b', dx)` are exact.
* **Edges** `W.edge(a, b, { route: 'elbow' | 'curve' | 'line', from: 'b' | ['b', dx], to: 't' | 'l' | 'r', via: [[x,y],…], bend, label, labelAt, tone, dashed, arrowSize })`;
  `edge.in(t, dur)` draws it on with a travelling pulse. A spine along the left margin is `from:'l', to:'l', via:[[64, a.y],[64, b.y]]`.
* **Layout** `W.outline(parent, items)` (bracketed list under a parent), `W.grid(items)`, `W.layout(ids, edges)` (layered auto-layout), or place by hand.
* **Camera** `W.go(t, id, { fit: zone | rect | [ids], max, pad, dur, anchor })` fits the final zone rect, so the framing is stable while content fills in.
  `W.cam(t, target, …)` moves without highlighting. Leaving a cluster fades it (nodes, zones, their edges), and so does anything shown earlier that the new view still catches and that is not part of the focus (`cull: false` on the call, or `keep: true` in a node spec, to keep things).
* Zones **grow** as their nodes appear (`W.finish()` at the end of `build`). `zone.in(t)` should be ≈ 0.3 s before the head node appears. Charts/figures that are not nodes go in `extra: [{ x, y, w, h, t }]`; with `t` they join the district at that time, without `t` from the start.
* `W.put(el, { x, y, anchor: 'c' | 'tl' | 'tc' })` places any element (charts, bodies, custom SVG) in world coordinates.
* Reveal times are recorded, so call things in chronological order within a world.

### Detail blocks

* `engine/body.js` `body(R, { x, y, scale, id })` → hologram figure; `LM` landmarks, `b.pt([bx, by])` → world px; `hotspot(R, host, at, {tone, t0})`, `flow(R, svg, pts, {t0})`, `callout(...)`.
* `engine/ecg.js` `beats(rateFn, {jitter, omit, seed})`, `ecgStrip(R, {w, h, bs, tone, fib})` live scrolling ECG strips + `strip.rate(fn, el)` for a bpm readout.
* `engine/charts.js` `thresholdBars` (functional classes: CCS / NYHA), `dayStrip` (doses per 24 h).
* `engine/components.js` `rich` (headline with word reveal), `status`, `counter`, `underline`, `drawPath`, `tile`.
* Low-level: `R.show / R.hide / R.tween(el, t, dur, {opacity,x,y,scale,rot,blur,'css:--var','attr:name'})`, `R.fn(t0, t1, cb)` (cb(progress, seconds), clamps at both ends), `R.icon(name)` (Lucide).

## Look

Dark ink, Instrument Serif headlines (gradient italic via `*word*`), Inter, JetBrains Mono micro labels. Categorical hues
pink / teal / violet (validated for all pairs on the dark surface); status colours good / warn / serious / crit are reserved
and always come with an icon and a label. Type in the world: step label 50 px, chips 44 (sm 38), tags 38, edge labels 36;
after the camera's zoom (≈ 1.0 – 1.5) nothing the viewer must read is below ~38 px. Keep ≥ 56 px side margins.

Zones of the 1080×1920 frame: HUD 104–150 · stage (world viewport) 180–1400 · captions end at y = 1560 · below 1560 is left to the app UI.

## Rules of thumb

1. Every sentence gets a visible event on its key word (node, edge, hotspot, count, highlight); no 3-second stretch without motion.
2. One idea per cluster; the camera frames the cluster's final extent so it never jitters while items arrive.
3. `node scripts/render.mjs <reel> --audit` must report 0 issues; then read a contact sheet at ≥ 8 times.
4. Last scene `exit: false` so the final composition holds to 60.000 s. First element visible by ~0.8 s.
5. Text must be faithful to the book; anything that is not in the book is a supplementary explanation and is flagged in `script.js`.
6. Never `pkill -f` with a pattern that appears in your own command line (it kills your shell); use `pkill -f "[r]ender.mjs <reel>"`.
