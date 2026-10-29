# Kafu MotionCards — scene authoring v2 (compact reference)

> **RETIRED (Oct 2026). Do not use this to make new content.** The owner stopped hand-animated MotionCards.
> New work is IMAGE LESSONS only: follow `motioncards/LESSON_PROMPT.md`. This file is kept only as background for
> the shared scaffold/package/validate tools.

> **GOLD STANDARD (read first):** follow [`GOLD_STANDARD.md`](GOLD_STANDARD.md), the owner-approved workflow, card format and visual method from MRCS chapters 20–25.

Read this file instead of the long docs when you only author scenes. Edit only `work/<batch>/scenes/Q#########.scene.json`. The tooling does selection, hashes and packaging (see `MASTER_PROMPT.md` for the commands).

v2 is opt-in per scene (`"schema_version": 2`). v1 scenes still work unchanged. New scaffolds are v2.

## Loop (do this for every card)

1. Write the scene.
2. `python tools/motioncards.py lint --workspace work/<batch>`: errors name the exact field, e.g. `scene_v2_invalid:layers[3].keys[1].fill:...`.
3. `python tools/motioncards.py render --workspace work/<batch> --out work/<batch>/render`: look at `<QID>_sheet.png` (phone + tablet frames). Fix overlaps, text off-stage, an empty first frame and cramped labels. This needs `pip install playwright`; skip it only if no browser is available.
4. Voice (ask the owner first: Kokoro or ElevenLabs): `~/.venvs/kafu-voice/bin/python voiceover/voiceover.py make --engine <kokoro|elevenlabs> --workspace work/<batch>` (one-time setup: `voiceover/bootstrap.sh`). Every new card ships with voice; keep the numbered captions short and speakable so `make` needs no edits.
5. `package` (it refuses a card without voice), then `validate`.

## Two ways to draw (mix them freely)

1. **Free mode (SVG + JavaScript): use it for anything professional or precise.** Write normal SVG and normal JavaScript, the way you already know them.
2. **Layers** (declarative JSON below): a shortcut for simple cards: titles, captions, arrows, particles and spotlights in a few lines.

### Free mode

```json
{"schema_version":2,"qid":"Q000000123","duration_ms":9000,"takeaway":"One sentence.",
 "stage":{"width":640,"height":560,"background":"#f4f8f8"},
 "layers":[{"type":"text","text":"Title","x":320,"y":50,"size":28,"weight":800,"max_width":600,"fit":true,"fixed":true}],
 "svg":"<svg><defs>...</defs><path id=\"vessel\" d=\"M ...\" fill=\"@artery\"/>...</svg>",
 "script":"function setup(api){ /* build once */ }\nfunction render(t, api){ /* draw frame at t ms */ }"}
```

- **`svg`:** any SVG markup: gradients, filters, masks, clipPaths, patterns, `<text>`, `<foreignObject>`. Its children are placed on the stage (stage coordinates; the root `<svg>` is only a wrapper). Colours can be `@tokens`. Images use `href="asset:<id>"`. It is checked for well-formed XML; errors report line and column.
- **`script`:** plain JavaScript with full DOM access inside the sandbox.
  - Define `function render(t, api)`, called for every frame with `t` in ms. Optionally define `function setup(api)`, called once before the first frame.
  - **Compute every frame only from `t`** (pure function of time). That keeps pause, seek and replay exact. `render` checks this and fails if a frame depends on the previous one.
  - Precompute in `setup`. Never accumulate state in `render`.
  - `setTimeout`, `setInterval` and `requestAnimationFrame` are inert, because the host owns the clock. `Math.random` is seeded; draw random values in `setup`.
  - The network is blocked: no external images, fonts or scripts. Embed images via `assets`.
  - Inline libraries are allowed if their licence permits it and they can be driven by `t` (seek/progress APIs).
  - The only text forbidden in code is `</script`, `<script` and `<!--`. Write `'<\/script'` if you need it in a string.
- **`api`:**

  | helper | what it does |
  |---|---|
  | `api.$(sel)`, `api.$$(sel)` | query the stage |
  | `api.el(tag, attrs, parent?)` | create an SVG element; strings may be `@tokens` |
  | `api.set(el, attrs)` | set attributes; numbers are rounded, `@tokens` resolved |
  | `api.seg(t, a, b, ease?)` | 0..1 progress between `a` and `b` ms, eased |
  | `api.ease(name, p)`, `api.clamp`, `api.lerp` | easing and maths |
  | `api.mixColor(c1, c2, p)` | colour interpolation |
  | `api.random(seed)` | seeded PRNG function |
  | `api.pointAt(pathEl, f)` | `{x, y, angle, length}` at fraction `f` along a path |
  | `api.asset(id)` | data URI of an asset |
  | `api.color(token)` | resolve a colour token |
  | `api.W`, `api.H`, `api.D`, `api.svg`, `api.hud` | stage width/height, duration, stage `<svg>`, fixed layer group |

- **Precision:** compute geometry from the real relationship instead of eyeballing it (e.g. a dissociation curve from the Hill equation, pressures from a formula). See `examples/v2-free-o2-curve.scene.json`.
- Errors come back with their location, e.g. `script line 12: Unexpected token`, `render(t=4200): api.set: element not found`, or `svg: not well-formed XML at line 3, column 9`.

### Layers scene

```json
{"schema_version":2,"qid":"Q000000123","duration_ms":9000,"takeaway":"One sentence.",
 "stage":{"width":640,"height":560,"background":"#fbfaf7"},
 "palette":{"name":"#hex"}, "gradients":[...], "assets":{...}, "camera":{"keys":[...]},
 "layers":[ ... ]}
```

- Stage default is 640×560, which reads well on phones (about 340×360) and tablets. Coordinates are stage pixels; y grows downward.
- Free-mode `svg` is drawn first (back), then layers in order, then `custom_renderer`. At most 400 layers in total (groups included).
- **The first frame (t=0) must not be empty.** The app shows it before Play.

## Timing model (the important part)

| field | meaning |
|---|---|
| `show: [start,end]` | when the layer exists (default: whole card) |
| `enter` | entrance at `start`: `fade` `pop` `grow` `draw` `type` `slide_up/down/left/right`, or `{"effect":"pop","ms":600,"ease":"back_out"}` (default 450 ms) |
| `exit` | leave at `end`: `fade` `shrink` `slide_*` (only when `end` < duration) |
| `keys` | `[{"t":ms, prop:value, "ease":"..."}]`: absolute ms; holds the first value before and the last value after. `ease` shapes the segment arriving at that key (default `ease_in_out`) |
| `repeat` | `{"every_ms":1200,"from_ms"?,"times"?}`: key `t` values are then inside one cycle (0..every_ms). Use it for heartbeat, pulses, rotation |

Easings: `linear ease_in ease_out ease_in_out sine back_out back_in elastic_out bounce_out step`.

Animatable in `keys`:
- **All layers:** `x` `y` (offset), `scale` `scale_x` `scale_y` `rotate` (around the layer's own centre, or `origin:[x,y]`), `opacity`.
- **Stroked shapes:** `draw` (0..1, line drawing itself), `fill` `stroke` (hex, rgb, hsl or `@token`), `stroke_width`.
- **Geometry:**
  - rect: `width` `height` `rx`
  - circle: `cx` `cy` `r`
  - ellipse: `cx` `cy` `rx` `ry`
  - line/arrow: `x1` `y1` `x2` `y2` (and `bend` for arrows)
  - path: `d` (morph; same commands and number count, no `A` arcs)
  - particles: `speed`
  - spotlight: `cx` `cy` `r` / `x` `y` `width` `height`, `dim`
- **Along a path:** `progress` (0..1), for layers with `along`.
- **Text:** `fill`.

## Layer types

Common fields: `id`, `fixed` (top level only; ignores the camera, use it for titles and captions), `opacity`, `fill`, `stroke`, `stroke_width`, `fill_opacity`, `stroke_opacity`, `dash:[8,6]`, `linecap`, `linejoin`, `shadow` (`true`/`"soft"`/`"strong"`), `glow:"#hex"`, `blur`, `origin`, `along:{"d":"M..","rotate":true}`.

| type | fields |
|---|---|
| `rect` / `highlight` / `focus` | `x y width height rx`. `highlight` is a translucent yellow wash; `focus` is a dashed outline |
| `circle` | `cx cy r` |
| `ellipse` | `cx cy rx ry` |
| `line` | `x1 y1 x2 y2` |
| `arrow` | `x1 y1 x2 y2`, `bend` (curve, px), `head` (`end`/`start`/`both`/`none`), `head_size` |
| `path` | `d` (SVG path) |
| `polygon` / `polyline` | `points:[[x,y],...]` |
| `text` (alias `label`) | `text` (`\n` = new line), `x y` (**y = vertical centre**), `size weight color anchor font` (`sans`/`serif`/`mono`/`rounded`), `italic`, `max_width` (auto wrap), `fit` + `max_lines` (auto shrink), `box:{fill,stroke,pad,rx}` (label pill), `halo` (outline colour for legibility), `letter_spacing`. Arabic is detected automatically |
| `group` | `x y` (offset for children), `layers:[...]`. Children keep their own timing; the group's keys and effects apply to all of them |
| `particles` | `d` (track), `count` (≤200), `r`, `shape` (`dot`/`ring`/`rbc`), `speed` (px/s, can be keyed), `spread` (px across the track), `seed`, `size_jitter`, `phase`, `guide:{stroke,stroke_width,dash,opacity}` (draws the track), `fade_ends` |
| `spotlight` | dims everything except a circle (`cx cy r`) or box (`x y width height rx`); `dim` (default 0.6), `color`. Key the geometry to walk the eye through steps |
| `image` | `asset` (id from `assets`), `x y width height`, `fit` (`contain`/`cover`/`stretch`) |

## Start from the bundled art library (best results, fewest tokens)

Hand-drawn anatomy from a language model looks flat and amateur however carefully it is coded. The cards that look professional start from real medical illustrations. The repo ships a licence-checked library in `motioncards/library/` that works offline:

```bash
python tools/motioncards.py library                      # list: lib:healthy-lung, lib:heart, lib:stomach, ...
python tools/motioncards.py style-kit work/b/scenes/Q….scene.json
python tools/motioncards.py import-svg lib:healthy-lung --scene work/b/scenes/Q….scene.json --id lungs --box 100,96,440,450
```

**Where to find art, in this order** (best quality and same style first; details, URL patterns and credits are in "Approved art sources" below):

| Need | Look here first | Then |
|---|---|---|
| Organs, anatomy, cells | `motioncards.py library` (offline) | Servier SVGs: search [bioicons.com](https://bioicons.com/) (set the licence filter to CC BY 3.0 and pick drawings by Servier), then import from the raw GitHub URL (pattern in row 1 below). Sections and regions: [Togo Picture Gallery](https://togotv.dbcls.jp/en/pics.html). Pathology and microbes: [NIAID BioArt](https://bioart.niaid.nih.gov/) (PD or CC BY entries only). Fine surgical anatomy: [Gray's Anatomy plates](https://commons.wikimedia.org/wiki/Category:Gray%27s_Anatomy_plates) |
| People, patients, doctors, lifestyle (sitting, running, cycling, lifting, obesity, smoking, hygiene, age) | Servier SMART: search [smart.servier.com](https://smart.servier.com/) (e.g. `https://smart.servier.com/?s=cyclist`) or browse [People](https://smart.servier.com/category/general-items/people/), [Food](https://smart.servier.com/category/general-items/food/), [Equipment](https://smart.servier.com/category/general-items/equipment/); download the set's `.pptx` and cut the drawing out with `tools/motioncards_smart.py` | Servier SVGs on [bioicons.com](https://bioicons.com/) in `General_items`, `Animals`, `Plants_Algae`, `People-Other` |
| Food, drink, weather, seasons, day/night, animals, everyday objects | Servier SVGs on [bioicons.com](https://bioicons.com/) (`General_items`, `Animals`, `Plants_Algae`) | SMART Food or Risk-Factors sets |
| Small symbols (warning, drug, device) | [Health Icons](https://healthicons.org/) | [Fluent Emoji](https://github.com/microsoft/fluentui-emoji) as a small prop only |
| House, river, landscape, vehicles | No approved source matches Servier quality yet. Draw a simple setting with the style kit | A small [Noto](https://github.com/googlefonts/noto-emoji/tree/main/2D/svg) or Fluent emoji, or a [Kenney](https://kenney.nl/assets) vector pack |
| Real ECG or rhythm strip | [PTB-XL](https://physionet.org/content/ptb-xl/): a real 12-lead ECG drawn as an SVG path (row M5) | Draw a stylised trace with the style kit |
| Drug or molecule structure | [RDKit](https://www.rdkit.org/), drawn from the [PubChem](https://pubchem.ncbi.nlm.nih.gov/) SMILES (row M6) | Health Icons `medications` for a simple pill or syringe |
| Receptors, channels, molecules, cell types | Servier (`Receptors_channels`, `Cell_membrane`, `Intracellular_components`, `Blood_Immunology`) | [Reactome icons](https://reactome.org/icon-lib) (row M3) |
| Parasites, vectors (mosquito, tick, flea), animal silhouettes | Servier `Parasites` (62 drawings) | [PhyloPic](https://www.phylopic.org/) (row M4) |
| Detailed heart, brain or skull, or how organs sit together | Servier `Human_physiology` (362 drawings) | [Wikimedia Commons](https://commons.wikimedia.org/) (row M1): Patrick J. Lynch, LadyofHats or NCI SEER |
| Neuroscience drawings (brain sections, neurons) | Servier | [SciDraw on Zenodo](https://zenodo.org/search?q=scidraw) (row M7) |
| Any icon or emoji, found by name | [Iconify](https://icon-sets.iconify.design/) (row M2): one URL per icon | The raw GitHub patterns in rows 6, 7 and E1–E3 |

`lib:` imports add the Servier credit automatically. Render once with a grid (draw lines every 20 px in `setup`) to read where the organs landed, then place your additions on that art.

**Style kit:** `style-kit` adds `<defs id="kit">` to the scene, once. Use it on everything you draw yourself, so your shapes look like they belong next to the art instead of flat clip-art:

| id | use |
|---|---|
| `filter="url(#kit-volume)"` | soft 3D shading for organs, tumours and large shapes (`kit-volume-sm` for thin vessels, nerves and bands) |
| `filter="url(#kit-gloss)"` | wet, glossy highlight (mucosa, muscle) |
| `filter="url(#kit-shadow)"` | soft drop shadow (label chips, a lifted organ) |
| `filter="url(#kit-glow)"` | glowing signal or highlight (nerve impulses, danger halo) |
| `fill="url(#kit-tissue)"` `kit-muscle` `kit-lung` `kit-tumour` `kit-bone` | radial organ fills, lit from the upper left |
| `stroke`/`fill="url(#kit-nerve)"` `kit-vein` `kit-artery` | cylindrical gradients for vertical nerves and vessels |

**Never put a kit filter or a kit gradient on a perfectly horizontal or vertical line.** Kit filters and gradients are sized to the element's bounding box. A flat line has zero height (or width), so it vanishes or is clipped to a sliver. Draw a band as a `rect` with `rx`, or use a solid colour.

Filters re-render whenever the element changes, so put them on static shapes or on shapes that only move, fade or scale. Never put one on an element that changes shape every frame and covers half the stage. In free mode, append your elements to the art's parent (`const P = api.$("#lungs").parentNode`) so they stack above the art. To put something behind the art, use `P.insertBefore(el, api.$("#lungs"))`.

## Professional illustrations from the internet (import, never paste)

Never paste a downloaded SVG into your reply: one medical illustration is 8k–25k tokens. Import it with the tool. The model then only references it by id.

```bash
# Place a drawing on the stage (box = x,y,width,height in stage px)
python tools/motioncards.py import-svg heart.svg --scene work/b/scenes/Q….scene.json --id heart --box 40,110,300,320 \
  --credit "Heart: Servier Medical Art, CC BY 4.0"
# Reusable symbol for many copies (box = width,height, centred on 0,0), drawn with <use href="#rbc">
python tools/motioncards.py import-svg erythrocyte.svg --scene … --id rbc --template --box 44,44 --credit "…"
```

The tool:
- strips DOCTYPE, metadata, editor junk and event handlers;
- rejects external links;
- scales the art into the box;
- makes every internal id and CSS class unique, so two files can never break each other's gradients;
- rewrites path data in its shortest form: absolute points are rounded first, then each segment is written absolute or relative (whichever is shorter), so rounding errors never add up;
- picks the precision automatically from the placement scale (worst-case error 0.1 stage px, invisible on phones and tablets). Offsets, stroke widths and radii keep 2 decimals. Override with `--decimals N`, but never use `0` on detailed art: thin vessels break;
- shortens colours (`#ffcc00` → `#fc0`);
- records the credit, which the card shows small in the corner.

Then animate it from `script`: `api.$('#heart')` (transform, opacity, filters, or parts by id), or `<use href="#rbc">` copies moved along paths.

## Recipes: tested animations (use them instead of writing your own)

`python tools/motioncards.py recipes work/b/scenes/Q….scene.json` adds `const R = {...}` to the scene script once, and adds the style kit too. Each recipe is a pure function of `t`, so pause and seek work, and each is covered by a browser test. The 9342 and 9343 cards dropped from about 3.0 KB to 1.4 KB of card code with the same result.

| Recipe (create in `setup`) | Animate in `render(t, api)` | Use for |
|---|---|---|
| `st = R.wrap(api, api.$("#st"))` | `R.seeThrough(api, st, f, 0.45)` | Fade imported art to reveal what lies behind it |
| `v = R.tube(api, P, d, "artery"\|"vein"\|"nerve"\|"bile"\|"gut", w, {behind: st})` | `R.drawOn(api, v, f)`, `R.squeeze(api, v, f, w0, w1)`; `v.p` is the centre path, `v.fill` its normal paint | Vessels, nerves, ducts, bowel |
| `fl = R.flow(api, P, v.p, {n, color, period, reverse, behind})` | `fl.update(t, on)` | Blood, bile, air or food moving along a tube |
| `im = R.impulses(api, P, nerve.p, {reverse})` | `im.update(t, on)` | Nerve signals, referred pain |
| `b = R.bleed(api, P, x, y, {angle, spread, reach, gravity})` | `b.update(t, on)` | Pulsatile arterial bleeding, with a pulsing ring |
| `dr = R.drip(api, P, x, y)` | `dr.update(t, on)` | Oozing or venous bleeding |
| `l = R.lump(api, P, cx, cy, "tumour"\|"cyst"\|"mass"\|"artery", {behind})` | `l.update(t, f, rx, ry, pulse)` | Tumours, cysts, masses, aneurysms |
| `u = R.ulcer(api, P, x, y, {rx, ry})` | `u.update(t, f)` | Ulcers, craters, perforations |
| `gl = R.glow(api, P, x, y, {r, color})` | `gl.update(t, on)` | Pain, inflammation, danger |
| `tr = R.travel(api, P, d, {width})` | `tr.update(t, f)` | Hernia sac, catheter, bolus, stone travelling a route |
| `L = R.callout(api, P, "text", x, y, color, [toX, toY])` | `R.fade(api, L, t, in0, in1, out0, out1)` | Label chip with a leader line |
| `th = R.thermometer(api, P, x, y0, y1, lo, hi, {ticks})` | `th.update(v, color)` | Body or room temperature: tube top at `y0`, bulb at `y1`, scale `lo`..`hi` °C, optional tick values, live °C label |
| `sw = R.sweat(api, P, [[x, y, size], ...])` | `sw.update(t, f)` | Sweat or any liquid beading up drop by drop (`f` 0..1 = how wet) |
| `a = R.arrowGrow(api, P, d, color, w)` | `a.update(t, f)` | Arrow that grows along any path `d`: heat loss, flow direction, cause → effect |
| `R.scaleAbout(api, el, s)` | | Grow or pulse a shape about its own centre |

`P` is the art's parent (`R.layer(api, "#st")`), so new elements stack above the art; pass `{behind: st}` to put them behind it. `R.grid(api)` draws a 20 px layout grid; `lint` warns until you remove it. Write your own code only for what no recipe covers.

### Approved art sources (use only these, in this order)

Checked October 2026 for Kafu's goals: MRCS clinical anatomy, vector art whose parts can be animated, one consistent style, and commercial use with modification allowed. The licence on each individual file always wins.

| # | Source | Use it for | Licence: what you may take | Credit to pass to `--credit` |
|---|---|---|---|---|
| 0 | **Bundled library**: `motioncards.py library`, then `import-svg lib:<name>` | First choice: thorax, heart, lungs, upper GI. Works offline | CC BY 3.0 (Servier) | added automatically |
| 1 | **Servier Medical Art** via bioicons: `https://raw.githubusercontent.com/duerrsimon/bioicons/main/static/icons/cc-by-3.0/<Category>/Servier/<name>.svg` (categories include `Human_physiology`, `Oncology`, `Blood_Immunology`) | Any organ or system not in the library. **Default style for every card** | CC BY 3.0 (these copies) | `"<What>: Servier Medical Art, CC BY 3.0"` |
| 2 | **Togo Picture Gallery (DBCLS)**: archive with the bulk SVG zip and English tag CSV at `https://dbarchive.biosciencedbc.jp/data/togo-pic/` (read `LATEST/README_e.html`); single pictures at `https://togotv.dbcls.jp/en/togopic.<year>.<number>.html` | Anatomical sections and regions Servier lacks. Flatter style: **never mix it with Servier in one card** | CC BY 4.0 (whole database) | `"<What>: Togo Picture Gallery © DBCLS, CC BY 4.0"` |
| 3 | **NIH BioArt Source (NIAID)**: `https://bioart.niaid.nih.gov/` | Pathology, microbiology, immunology, cells | **Only entries marked Public Domain or CC BY.** Never BY-NC, BY-ND or BY-SA | `"<What>: NIAID NIH BioArt Source (bioart.niaid.nih.gov/bioart/<id>), <licence>"` |
| 4 | **Gray's Anatomy (1918) SVG redraws** on Wikimedia Commons (search `Gray<plate number> svg`) | Fine surgical anatomy: inguinal canal, rectus sheath, nerve courses. Old line art: shade it with the style kit | Public domain (US); check that the file page says so | `"<What>: Gray's Anatomy 1918 (H. V. Carter), public domain; vector by <Commons author>"` |
| 5 | **Mikael Häggström diagrams** on Wikimedia Commons (gallery: `https://en.wikiversity.org/wiki/WikiJournal_of_Medicine/Medical_gallery_of_Mikael_H%C3%A4ggstr%C3%B6m_2014`) | Whole-body maps: symptoms, organ positions | CC0 for the 2014 gallery; check newer files | `"<What>: Mikael Häggström, CC0"` |
| 6 | **Health Icons**: `https://raw.githubusercontent.com/resolvetosavelives/healthicons/main/public/icons/svg/{outline,filled}/<category>/<name>.svg` (categories include `body`, `symbols`, `medications`, `devices`, `conditions`) | Small symbols only (warning, drug, device). Never the main picture | CC0 | none needed |
| 7 | **Tabler Icons**: `https://raw.githubusercontent.com/tabler/tabler-icons/main/icons/outline/<name>.svg` | UI marks only: arrows, ticks, crosses | MIT | none needed |

#### More medical sources (M1–M7: when Servier has nothing)

> **Gold-standard cards do not use M1–M7.** `GOLD_STANDARD.md` stays Servier-only (bioicons, SMART, `lib:`), with the style kit for the rest. Use these rows only when the owner asks for them for a batch.

Tested on 9 October 2026 from a Claude Code cloud container: each source was downloaded and imported with `import-svg`. Licences were read from each source's own page or API. The licence on each individual file still wins. Accept only public domain, CC0 or CC BY; never NC, ND or SA.

| # | Source and URL pattern | Use it for | Licence | Credit to pass to `--credit` |
|---|---|---|---|---|
| M1 | **Wikimedia Commons**, direct file: `https://upload.wikimedia.org/wikipedia/commons/<a>/<ab>/<File_name>`, where `<ab>` is the first 2 hex characters of the MD5 of the file name (underscores, not spaces) and `<a>` is the first one (recipe below). Best authors: **Patrick J. Lynch** (heart, brain, skull), **LadyofHats / Mariana Ruiz** (skeleton, cells, organs), **NCI SEER Training** (organ relations) | Detailed line art and anatomy that Servier lacks | Per file: read `LicenseShortName` from the API (recipe below). Lynch: CC BY 2.5. LadyofHats and SEER: public domain | Lynch: `"<What>: Patrick J. Lynch, medical illustrator; C. Carl Jaffe, MD, cardiologist, CC BY 2.5"`. Others: `"<What>: <Artist> (Wikimedia Commons), <licence>"` |
| M2 | **Iconify**: `https://api.iconify.design/<set>/<name>.svg`; find names with `https://api.iconify.design/search?query=<word>&prefixes=healthicons,material-symbols` | Small icons and emoji, found by name. Sets: `healthicons` (2,042), `material-symbols` (15,728, e.g. `ecg-heart`), `fluent-emoji-flat` (3,145), `noto` (3,729), `twemoji` (3,988). **Never `openmoji`** (CC BY-SA) | Health Icons CC0; Material Symbols and Noto Apache 2.0; Fluent MIT; Twemoji CC BY 4.0 | Same as rows 6 and E1–E3; Material Symbols: `"<What>: Material Symbols (Google), Apache 2.0"` |
| M3 | **Reactome icon library**: `https://reactome.org/icon/R-ICO-<number>.svg`; browse and search at `https://reactome.org/icon-lib` | 1,500+ receptors, channels, molecules, cell types and tissues. Flat style: keep it small next to Servier | CC BY 4.0 (`reactome.org/license`) | `"<What>: Reactome (reactome.org), CC BY 4.0"` |
| M4 | **PhyloPic**: `https://images.phylopic.org/images/<uuid>/vector.svg`; find the uuid on `https://www.phylopic.org/` | One-colour silhouettes: mosquito, tick, flea, worms, animals | Per image (shown on the image page): use only CC0, Public Domain Mark or CC BY | `"<What>: <contributor>, PhyloPic, <licence>"` (none needed for CC0 or public domain) |
| M5 | **PTB-XL ECG database** (PhysioNet): `https://physionet.org/files/ptb-xl/1.0.3/records100/<NNNNN>/<NNNNN>_lr.{hea,dat}`. Find a rhythm in `ptbxl_database.csv` (column `scp_codes`, e.g. `NORM`, `AFIB`, `CLBBB`; column `filename_lr` gives the path) | Real ECG traces, 21,799 12-lead recordings of 10 s each. Draw one lead as a path and reveal it with `R.draw` or a moving clip | CC BY 4.0 | `"ECG: PTB-XL (PhysioNet), CC BY 4.0"` |
| M6 | **RDKit** (`pip install rdkit`, BSD) with a SMILES from PubChem: `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/<drug>/property/SMILES/TXT` | Drug and molecule structures for pharmacology cards | Chemical structures are facts; RDKit is BSD | `"<Drug> structure: drawn with RDKit"` |
| M7 | **SciDraw** drawings on Zenodo: `https://zenodo.org/api/records/<id>` (gives `metadata.license` and `files[].links.self`) | Brain sections, neurons, lab animals | CC BY 4.0 (check `metadata.license`) | `"<What>: <creator>, SciDraw (Zenodo <id>), CC BY 4.0"` |

Recipes (copy and edit):

```bash
UA="KafuMotionCards/1.0"   # Wikimedia and PubChem refuse requests without a User-Agent and rate-limit (429): one request at a time, -f + --retry
# M1: download File:<name> from Wikimedia Commons, then read its licence and author
name="Skull_and_brain_normal_human.svg"; h=$(printf %s "$name" | md5sum | cut -c1-32)
curl -sLf --retry 3 --retry-delay 5 --max-time 60 -A "$UA" -o brain.svg "https://upload.wikimedia.org/wikipedia/commons/${h:0:1}/${h:0:2}/$name"
curl -sf --retry 3 --retry-delay 5 --max-time 60 -A "$UA" "https://commons.wikimedia.org/w/api.php?action=query&titles=File:$name&prop=imageinfo&iiprop=extmetadata&iiextmetadatafilter=LicenseShortName|Artist&format=json"
# M6: a drug structure as SVG
smiles=$(curl -sf --retry 3 --retry-delay 5 --max-time 60 -A "$UA" https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/aspirin/property/SMILES/TXT)
python3 -c "import sys;from rdkit import Chem;from rdkit.Chem.Draw import rdMolDraw2D as D;d=D.MolDraw2DSVG(300,200);D.PrepareAndDrawMolecule(d,Chem.MolFromSmiles(sys.argv[1]));d.FinishDrawing();open('aspirin.svg','w').write(d.GetDrawingText())" "$smiles"
```

```python
# M5: one lead of a PTB-XL record as an SVG path (100 Hz file: 10 s = 1,000 samples per lead, 12 leads)
import numpy as np, urllib.request as u
base = "https://physionet.org/files/ptb-xl/1.0.3/records100/00000/00001_lr"   # from filename_lr in ptbxl_database.csv
for ext in ("hea", "dat"): u.urlretrieve(f"{base}.{ext}", f"rec.{ext}")
hea = open("rec.hea").read().split("\n"); nsig, n = int(hea[0].split()[1]), int(hea[0].split()[3])
gain = float(hea[1].split()[2].split("(")[0].split("/")[0])                  # ADC units per mV
mv = np.fromfile("rec.dat", "<i2").reshape(n, nsig)[:, 1] / gain              # column 1 = lead II
pts = " ".join(f"{i * 600 / n:.1f},{100 - v * 60:.1f}" for i, v in enumerate(mv))
open("ecg.svg", "w").write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 200"><polyline fill="none" stroke="#c62828" stroke-width="2" points="{pts}"/></svg>')
```

Notes for agents:
- **Check the size after every import.** If one drawing adds more than about 100 KB to the scene, choose another file. The NCI SEER pancreas SVG is 886 KB and still added 560 KB, because it is 1,701 traced paths.
- **Wikimedia rate limits.** From cloud containers, its search API and `Special:FilePath` often answer 429 (too many requests). The direct `upload.wikimedia.org` URL above worked. Find file names with a web search, send a User-Agent, and go slowly.
- **NIAID BioArt (row 3)** has no direct file URL or API an agent can use. Use it only when the owner supplies the file.
- **Not usable by agents today:** Blausen and OpenStax figures (PNG only; `import-svg` takes SVG), LUMC/AnatomyTOOL drawings marked NC or SA, and Radiopaedia (NC).

#### Everyday art (non-medical: people, lifestyle, food, animals, weather, equipment)

Checked 8 October 2026: each licence was read from the project's own licence file or page, and samples were imported with `import-svg` and rendered next to `lib:heart`.

**Start with Servier: it is the same artist and style as the library, so a card stays uniform.** Servier draws far more than organs:

| # | Source | What is there | Licence | Credit to pass to `--credit` |
|---|---|---|---|---|
| S1 | **bioicons Servier, everyday folders** (plain SVG, same URL pattern as row 1): `.../cc-by-3.0/General_items/Servier/<name>.svg`, `.../Animals/Servier/<name>.svg`, `.../Plants_Algae/Servier/<name>.svg` | 162 general items: food and drink (bread, glass-water, milk, burger, wine, salt), seasons and weather (sun, summer, winter, autumn, spring, day, night, heat, uv-radition), toilet, bath, faucet, hand-washing, cigarette, clock, stopwatch, scale, traffic lights, ventilator, arrows. 52 animals (dog, cat, horse, ox, sheep, pig, fish, mouse, rat), 21 fruits and vegetables | CC BY 3.0 | `"<What>: Servier Medical Art, CC BY 3.0"` |
| S2 | **SMART Servier PowerPoint sets** (vector shapes, not SVG): `https://smart.servier.com/wp-content/uploads/2016/10/SMART-<Set>.pptx`. Useful sets: `People` (newborn to elderly, all ethnicities, clothed and unclothed), `Risk-Factors` (tobacco, alcohol, excess weight, obesity, age, hygiene, sitting, running, cycling, lifting, raised legs, day/night, clock, heat, UV), `Dietetics`, `General-items`, `Medical-acts`, `Medical-equipment`; also `.../2025/06/SMART-Emergency-equipment.pptx` | Every page says: "Servier Medical Art is licensed under CC BY 4.0 … even for commercial purposes" | `"<What>: Servier Medical Art (smart.servier.com), CC BY 4.0"` |

Get one drawing out of a SMART set with `tools/motioncards_smart.py` (needs LibreOffice, `pdftocairo` and the Chromium used by `render`):

```bash
python3 tools/motioncards_smart.py list SMART-Risk-Factors.pptx           # slide titles and the group name of each drawing (x = position on the slide, left to right)
python3 tools/motioncards_smart.py extract SMART-Risk-Factors.pptx 13 "Group 135" cyclist.svg
python3 tools/motioncards.py import-svg cyclist.svg --scene … --id cyclist --box 20,20,300,260 --credit "Cyclist: Servier Medical Art (smart.servier.com), CC BY 4.0"
```

Tested: cyclist, man lifting a box, patient with raised legs, day/sun and a clothed woman each import at 9–103 KB and render cleanly next to `lib:heart`. Each drawing comes out as many separate paths without names: move or fade it whole, or cross-fade two drawings. Do not try to animate limbs. If a slide has two groups with the same name, `extract` keeps both. Clothes are often separate groups drawn over a body: add them with `--also "Group 824"` (repeatable). Then crop the scene box, or pick another slide.

**Still missing from Servier: houses, rivers, landscapes and vehicles other than a bicycle and an ambulance.** No source we found is both permissive and drawn as finely as Servier. The best-looking one, the IAN/UMCES symbol library (3,000+ SVG landscapes, rivers, animals, buildings), is **CC BY-SA 4.0**, so it is excluded until the owner decides otherwise. Until then, draw a simple setting yourself with the style kit, or use a small prop from the emoji sets below. Never make an emoji the main picture.

**Small props only (when S1/S2 have nothing):** pick one family per card.

| # | Source | Use it for | Licence: what you may take | Credit to pass to `--credit` |
|---|---|---|---|---|
| E1 | **Microsoft Fluent Emoji**, Color style: `https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/<Name>/Color/<name>_color.svg` (e.g. `assets/Dog/Color/dog_color.svg`; folder names have spaces, encode them as `%20`; people with skin tones use `<Name>/Default/Color/<name>_color_default.svg`). Flat style: `.../<Name>/Flat/<name>_flat.svg` | About 1,600 subjects. Of the emoji sets, its soft gradients sit best next to Servier. Color is 5–22 KB per drawing and uses SVG filters, so keep it static or only move/fade it; use Flat (about 2 KB, no filters) when a card needs many copies. **Before importing a Color or Flat file, apply the root-fill fix below** | MIT (`LICENSE`: "Permission is hereby granted … to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies"). The 3D style is PNG only: do not use it | `"<What>: Microsoft Fluent Emoji, MIT"` |
| E2 | **Google Noto Emoji**: `https://raw.githubusercontent.com/googlefonts/noto-emoji/main/2D/svg/emoji_u<codepoint>.svg` (lowercase hex, sequences joined with `_`, e.g. `emoji_u1f3de.svg` = national park) | Rounded flat colour, 3–9 KB, clean separate shapes. Good landscapes and buildings | Apache 2.0 (`2D/svg/LICENSE`). The fonts are OFL and the `3D/` folder is PNG only: use only `2D/svg` | `"<What>: Google Noto Emoji, Apache 2.0"` |
| E3 | **Twemoji** (maintained fork): `https://raw.githubusercontent.com/jdecked/twemoji/main/assets/svg/<codepoint>.svg` (lowercase hex, sequences joined with `-`) | The lightest (1–3 KB), simplest flat shapes; good for small repeated symbols (sun, raindrop, snowflake) | Graphics CC BY 4.0 (`LICENSE-GRAPHICS`; README: "The graphics are licensed under the CC-BY 4.0") | `"<What>: Twemoji (github.com/jdecked/twemoji), CC BY 4.0"` |
| E4 | **Kenney** 2D packs: download the pack zip from `https://kenney.nl/assets/<pack>`; use only packs whose zip has a `Vector/` folder (e.g. Fish Pack) | Game-style scenery: terrain, water plants, rocks, fish, simple props. Tiny files (1–2 KB) with separate shapes. Coverage is spotty; most packs are PNG or 3D | CC0 (`License.txt` in every zip: "You can use this content for personal, educational, and commercial purposes") | `"<What>: Kenney (kenney.nl), CC0"` (optional) |
| E5 | **Open Peeps** (Pablo Stanley): single files linked from `https://www.openpeeps.com/`; whole library from `https://gum.co/openpeeps` (enter 0 to download free) | People in black-and-white line art: a patient sitting, a person shrugging. Each peep is about 12 KB after import, with separate head, body and arm groups | CC0 (site: "The library is in the public domain under the CC0 License … even for commercial purposes, without asking permission") | `"<What>: Open Peeps by Pablo Stanley, CC0"` (optional) |

**Root-fill fix (Fluent Emoji and other Figma exports).** `import-svg` drops attributes on the root `<svg>`. Fluent files put `fill="none"` there, so their stroke-only paths turn into black blobs after import. Wrap the content in a group first, then import the fixed copy:

```bash
python3 -c "import re,sys;s=open(sys.argv[1]).read();m=re.search(r'<svg[^>]*>',s);open(sys.argv[2],'w').write(s[:m.end()]+'<g fill=\"none\">'+s[m.end():].replace('</svg>','</g></svg>'))" dog_color.svg dog_fixed.svg
```

Rules for everyday art:
- **One emoji family per card.** Never mix Fluent, Noto and Twemoji, or emoji with Open Peeps line art, in one card. Servier art (medical, S1 or S2) is always the main picture.
- Leave out logos, brand glyphs and flags.
- Render once and check the result: an import that looks fine as a file can still break (see the root-fill fix).

**Maybe (use only if S1, S2 and E1–E5 have nothing that fits, and say so in the reply):**

| Source | Licence | Why not first choice | Credit |
|---|---|---|---|
| **Humaaans** and **Open Doodles** (Pablo Stanley): `https://gum.co/humaaans`, `https://www.opendoodles.com/` | CC0 (each site says so) | Downloads go through Gumroad or Dropbox, so no stable per-file URL. Not render-tested yet | `"<What>: Humaaans by Pablo Stanley, CC0"` / `"<What>: Open Doodles by Pablo Stanley, CC0"` |
| **Openclipart**: `https://openclipart.org/` (copies at `https://freesvg.org/`) | CC0 per upload (FAQ) | The site timed out during the check. Every file has a different style and quality; check the file page | `"<What>: <artist>, Openclipart, CC0"` |
| **game-icons.net**: `https://raw.githubusercontent.com/game-icons/icons/master/<author>/<name>.svg` | CC BY 3.0, or CC0 where `license.txt` says so ("Please, include a mention 'Icons made by {author}'") | One-colour silhouettes only. Each file starts with a black 512×512 square: delete the first `<path>` before importing | `"<What>: <author>, game-icons.net, CC BY 3.0"` |
| **Streamline Emojis**: the `@iconify-json/streamline-emojis` package on jsDelivr (no per-file URL; extract the icon from `icons.json`) | CC BY 4.0 (`webalys-hq/streamline-vectors` README: "You must give appropriate credit and provide a link to the Streamline website"). Only the sets marked CC BY 4.0; other Streamline free sets have a restrictive licence | Cartoon outline style that clashes with Servier | `"<What>: Streamline (streamlinehq.com), CC BY 4.0"` |
| **Mozilla FxEmoji**: `https://github.com/mozilla/fxemoji` | Visual design CC BY 4.0 (`LICENSE.md`); the code is Apache 2.0, and Iconify wrongly lists the art as Apache | Old set (2015), smaller, dated style | `"<What>: Mozilla FxEmoji, CC BY 4.0"` |

**Do not use** (checked 8 October 2026):

| Source | Why |
|---|---|
| OpenMoji | CC BY-SA 4.0: share-alike would force the cards' licence |
| IAN/UMCES symbol libraries | CC BY-SA 4.0 (beautiful; owner decision needed, see above) |
| unDraw | Licence forbids compiling the assets "to replicate a similar or competing service" or distributing them "in packs or otherwise" |
| CocoMaterial | The creator's announcement forbids compiling the illustrations to replicate the service (same trap as unDraw); its licence page could not be read |
| DrawKit | Own non-transferable licence, not an open licence |
| IRA Design | Claims MIT but is governed by Creative Tim's EULA: "You can't redistribute or resell our products source files as they are" |
| illlustrations.co | Newer and premium assets are under a licence that forbids redistribution and competing libraries |
| Noto Emoji `3D/`, Fluent Emoji 3D | PNG only |
| SVG Repo, Flaticon, Iconscout, Icons8 (Ouch!), Storyset, Freepik, Blush, other stock sites | Per-file or proprietary licences, attribution traps, or no redistribution |

Do not use other sources (Lottie, GSAP, 3D model sites, raster galleries such as Blausen or OpenStax, stock sites, Noun Project, Freepik) unless the user approves. They either do not fit the cards or their licence is unsafe for a paid app. If no approved source has the structure you need, draw it yourself with the style kit; never trace a textbook figure.

If the network cannot reach a source, say so and use the bundled library or the style kit. Do not substitute an unapproved site.

Rules:
- **Never use NC (non-commercial) or ND (no-derivatives) material.** Cards are modified, and the app may be paid. `import-svg` refuses a credit containing NC or ND.
- Never use images whose licence you cannot name. Never trace copyrighted textbook figures.
- Write the credit as `"<what>: <author/source>, <licence>"`, using the exact form in the table above.

Quality rules:
- Keep one art style per card; do not mix flat icons with detailed illustrations.
- Check anatomical correctness of the chosen drawing against the source question.
- Animate the teaching relationship (flow, change, sequence) on top of the art; do not just show a static picture.
- Move imported art with rigid changes: position, rotation, scale, opacity, colour, `<use>` copies and drawn-on paths. Language models are reliably weak at non-rigid deformation of organic shapes, so **do not morph complex organic outlines**. Swap or cross-fade between two drawings instead (as the sickle example does).

## Improving the library (trusted automatic process)

When a card needs something genuinely new and reusable, such as a drawing the library lacks or an animation you had to write that other cards will need, propose it. The owner approved automatic merging for proposals that pass the gate. Propose only what makes future cards **better or easier**, never something that adds choice without value.

**Propose when all of these hold:**
- You used it in a real card (list the QIDs in `used_in`), and it worked in the render.
- Nothing in the library already covers it. Check `motioncards.py library` and the recipes table first.
- It is general: another card on a different question could use it unchanged.
- For art: an approved source and licence (CC0, public domain, CC BY 3.0/4.0, MIT), in the same style family as the library (`servier`, `togo` or `other`).

**Do not propose:** card-specific code, tweaks to existing entries or recipes, near-copies of existing art, unlicensed or NC/ND/SA art, or anything you are not sure improves the result. When in doubt, don't propose.

**How (Claude Code sessions):**
1. `git checkout -b library/<short-name> origin/main`
2. Add the drawing to `motioncards/library/art/` and its entry in `library.json` with **every** field: `file`, `view`, `use`, `license`, `source` (https URL of the original), `credit`, `style`, `reason` (why it is an improvement), `used_in` (QIDs). For an animation: add the member to `const R` in `recipes.js` (append; never edit an existing one) and a demo `motioncards/library/demos/<name>.js` that uses it.
3. Run `python tools/motioncards.py library-check --base origin/main`. Fix every ❌ until it says PASS.
4. Commit, push, and open a PR to `main` titled `library: <what>`.

The **MotionCards library auto-merge** workflow then reruns the gate and the MotionCards test suite. It merges only if both pass; otherwise it comments with the reasons and leaves the PR for the owner.

**What the gate enforces:**
- Only library files change.
- Existing entries, recipes and the style kit stay byte-for-byte identical.
- At most 6 drawings and 3 recipes per proposal.
- Licence, credit, source, reason and `used_in` are all present.
- Each drawing imports cleanly, stays under 150 KB, validates and lint-checks clean, renders, and is not a near-duplicate of existing art.
- Each recipe has a demo that renders on phone and tablet with deterministic seeking.
- `recipes.js` stays under 40 KB.

**claude.ai sessions (no git):** put the same files under `work/<batch>/library-proposal/` (`art/…`, `entry.json`, `demos/…`) and mention it in your reply. The owner passes it to a Claude Code session, which runs the steps above.

## 3D (possible, rarely worth it)

three.js runs inside a card (tested: WebGL works in the sandbox under the production CSP). It costs about 640 KB per card, because each card is self-contained. It is heavier on phones and offline storage. The `render` determinism check covers SVG, not canvas pixels. Use 3D only when depth is the point (e.g. a spatial relationship), and get the geometry from a trusted model, not invented shapes.

## Colour

Built-in tokens, used as `"@name"`:
- **Interface:** `ink muted paper surface line accent good bad warn highlight info`
- **Anatomy and physiology:** `artery artery_dark vein vein_dark blood plasma nerve myelin muscle tendon bone cartilage fat skin mucosa lymph cell nucleus bile air water oxygen co2`
- **Agents:** `bacteria virus drug enzyme membrane`

Add your own with `"palette":{"name":"#hex"}` and use them as `@name`.

Gradients: `{"id":"g1","kind":"linear","angle":90,"stops":[{"offset":0,"color":"#fff"},{"offset":1,"color":"@surface"}]}` (radial: `cx cy r` from 0 to 1). Use one with `"fill":"url:g1"`. Gradients are static; they cannot be keyed.

## Camera

`"camera":{"keys":[{"t":0,"x":320,"y":280,"zoom":1},{"t":4000,"x":420,"y":300,"zoom":1.4,"ease":"sine"}]}`, where x/y is the point at the centre of the view. Mark titles and captions `"fixed":true` so the zoom does not crop them.

## Assets (real illustrations)

`"assets":{"heart":"data:image/webp;base64,..."}` (PNG, JPEG or WebP). Each asset is at most 600 KB and all assets together at most 1.2M characters. Use it for pre-drawn anatomy art, then animate it with `keys` and overlay arrows, particles and labels on top. Never copy copyrighted artwork.

## Custom renderer (legacy shortcut)

`"custom_renderer":"function renderCustom(layer,t,h){ h.el('circle',{cx:100+t/10,cy:50,r:8,fill:'@accent'}); }"` draws on a top layer that is cleared every frame. Prefer free mode (`svg` + `script`) for new work.

## Quality checklist (what makes a card look good)

- **One idea per card.** Three or four beats at most, each with a short caption, e.g. `"1 · ..."` captions as fixed text with `box` and `enter:"type"`.
- **Stage the eye.** Use one spotlight or camera move per beat. Fade the context instead of deleting it.
- **Motion has easing and purpose.** Use `back_out`/`pop` for appearance, `draw` for pathways, `particles` for flow, and `repeat` for rhythm. Avoid long slow fades: entrances should take 300–700 ms.
- **Text is legible on phones.** Use size ≥ 18 (titles 26–32) with `max_width` + `fit`, and keep it 30 px from the stage edges.
- **Use a consistent colour meaning** (e.g. `@good` for normal or physiological, `@bad` or `@accent` for pathology) and no more than 5 hues.
- **Hold the final state** for the last 1.5–2 s so the takeaway sinks in. The host then shows the Takeaway and the Correct answer.
- **Start from library art** (`lib:`) when an organ is shown; for an organ shown small, prefer the lighter drawing (e.g. `heart-front` 22 KB vs `heart` 62 KB), and draw only what changes (nerve, tumour, flow, wrap) with the style kit.
- **Accuracy beats decoration.** If you are unsure of a fact, simplify the drawing; never invent anatomy.
- **Morph only simple geometry** (a narrowing wall, a curve computed from an equation). For organic shapes, cross-fade between two real drawings.

## Token-saving patterns

- Use `enter` presets instead of keyframes.
- Use `@tokens` instead of hex.
- Use `group` + `x/y` to reuse coordinates.
- Use `repeat` instead of many keys.
- Use `particles` instead of many moving circles.
- Use `max_width` + `fit` instead of hand-tuned font sizes.

Gold examples:
- `examples/v2-free-o2-curve.scene.json`: free mode, computed physiology curve, professional chart styling;
- `examples/v2-imported-art-sickle.scene.json`: imported Servier cells reused with `<use>`, morph from normal to sickle, vaso-occlusion queue computed in `setup`;
- `examples/v2-stenosis-flow.scene.json`: layers; flow, morph, camera, particles;
- `examples/v2-synapse-steps.scene.json`: layers; stepwise mechanism, along-path, spotlight, captions.
