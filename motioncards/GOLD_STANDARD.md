# MotionCards gold standard (MRCS chapters 20–25)

> **RETIRED (Oct 2026). Do not use this to make new content.** The owner stopped hand-animated MotionCards.
> New work is IMAGE LESSONS only: follow `motioncards/LESSON_PROMPT.md`. This file is kept only as background for
> the shared scaffold/package/validate tools.

The owner approved the cards for chapters 20–22 and the rebuilt cards for chapters 23–25 (r2). Their method is the standard for every
new batch. The owner rejected the first version of chapters 23–25 ("not beautiful, confusing"), which used simple drawn shapes, tiny
cells and captions at the bottom. Do not repeat that.

Example videos (the look and pace to copy; the only MP4s kept in the repo): `motioncards/gold-standard-examples/`.

Reference scenes to open and copy from:
- `work/MRCS-CH20-22/scenes/*.scene.json`
- `work/MRCS-CH23-25/scenes/*.scene.json`

Good examples by type:

| Type | Scenes |
|---|---|
| Lens from an organ | `Q000009459`, `Q000009473`, `Q000009477` |
| Single big cell | `Q000009457` |
| Side-by-side comparison | `Q000009479` |
| Graph | `Q000009488` |
| Signalling network | `Q000009486` |

## 1. Batch workflow

1. **Input.** One owner export per chapter goes to `work/input/<BOOK>-ch<N>.export.json`. Several chapters can go into one package,
   and the adapter merges chapter metadata.
2. **Scaffold.** One workspace per batch:
   ```bash
   python3 tools/motioncards.py scaffold work/input/…ch23… work/input/…ch24… work/input/…ch25… \
     --out work/MRCS-CH23-25 --package-id MRCS-PARTA-550-2E-CH23-25 --revision 1 --qids <all QIDs> --duration-ms 7000
   ```
   This checks every question against its published hash. The duration is **7 s per card** unless the owner asks otherwise.
3. **Author each card** (sections 2–4 below). Large batches can be split across parallel agents, 3–4 cards each, all working from one
   written brief with this file, the reference scenes and the medical point of every card. Each agent rewrites only its own scenes, so
   one agent never edits another's cards.
4. **Lint** with `python3 tools/motioncards.py lint --workspace work/<batch>`. Every scene must PASS with no warnings.
5. **Render and look at every card:**
   ```bash
   python3 tools/motioncards.py render <scene> --out <dir> --times 300,1500,3500,5800,6900
   ```
   Look at the phone and tablet frames. Fix anything that overlaps, is cut off, or does not explain itself.
6. **Add voice** (rules in `voiceover/README.md`):
   ```bash
   ~/.venvs/kafu-voice/bin/python voiceover/voiceover.py make --engine <kokoro|elevenlabs> --workspace "$PWD/work/<batch>"   # ask the owner which engine first
   ```
   - Use an absolute workspace path.
   - If a line is too long for its beat, shorten only its `say` line in `voice/<QID>.voice.json`. The caption can stay.
   - Repeat until you get `CHECK PASS`.
   - If a word is misheard, rephrase the line or add the word to `voiceover/lexicon.json`.
   - If you change a caption, delete that card's voice files first.
7. **Package and validate:**
   ```bash
   python3 tools/motioncards.py package <exports…> --workspace work/<batch> --out dist/MCARDS_<ID>_r<N>.zip
   python3 tools/motioncards.py validate dist/MCARDS_<ID>_r<N>.zip
   ```
8. **Review video.** Join `work/<batch>/voice/review/*.mp4` with ffmpeg into one `REVIEW_<batch>_….mp4` **outside the repository**
   (for example the session's scratch directory), then delete `voice/review/`. Never commit an MP4 (`.gitignore` excludes `*.mp4`).
9. **Commit and deliver.** Commit the workspace, which is `input/`, `scenes/`, `selection.json`, and `voice/*.opus|*.json`. Commit the
   ZIP to `dist/`. Open a PR. Send the owner the ZIP and the review video in the conversation; the video is never kept in the repository.
10. **Rebuild or fix after delivery.** Raise `package_revision` in `selection.json`, set `"replace": true` in every changed scene,
    repackage as `_r<N+1>`, and delete the old ZIP from `dist/`.

## 2. Card format (fixed)

- **Scene basics.** `schema_version` 2, `duration_ms` 7000, a 640×560 stage, background `#f4f8f8`, and a one-sentence `takeaway`
  that stays faithful to the source explanation.
- **Title.** A text layer at y 44: size 26, weight 800, `max_width` 590, `fit`, `fixed`.
- **Captions.** Three text layers at **y 98, under the title**: size 20, weight 700, a white box with `@line`, `fixed`, enter and exit
  `fade`. They are numbered `1 · … / 2 · … / 3 · …` and shown at `[0,2300]`, `[2300,4600]` and `[4600,7000]`.
- **Content.** Everything else sits below y ≈ 125, usually on one white rounded panel.
- **Caption text.** Each caption is also the voice-over line: at most about 5 short spoken words, with no symbols and no option letters.
- **Three beats.** Each caption says exactly what moves in its window. Beat 1 sets the scene, beat 2 shows the mechanism, and beat 3
  gives the answer.

## 3. Visual method (what makes them clear)

1. **One story per card.** Show a recognisable organ or person on the left. When the answer is microscopic, put a round magnifier lens
   on the right, joined to the organ by dashed tangent connectors and clipped with a `clipPath`. The lens shows the cells at work.
2. **Real Servier art only.**
   - Servier SVGs from bioicons (CC BY 3.0). The local clone path and categories are in "Approved art sources" in `AUTHORING_V2.md`.
   - SMART people (CC BY 4.0).
   - `lib:` library art.
   - Repeat cells with `import-svg --template` and `<use>`.
   - Everyday objects (pills, cigarette, dye bottle, ball, cast, clock, X-ray...) use a real-looking emoji or icon as a small prop, not a
     plain shape: Fluent Emoji, Noto or Twemoji, or Health Icons (rows E1–E3 and M2 in `AUTHORING_V2.md`). One emoji family per card;
     never OpenMoji. Servier stays the main picture.
   - Only draw by hand what Servier lacks, such as a femur, a joint section, cytokines or receptors. Use the style-kit gradients
     (`url(#kit-bone)`, `kit-tissue`, …) and add `cellG` and `nuc` gradients as the references do.
   - Very large SVGs bloat the card (for example `hiv-virus` is about 400 KB). Redraw those in Servier style instead.
3. **Normal next to changed.** Show a dashed teal "ghost" of the normal state, or put normal cells on the left of the lens and changed
   cells on the right, so the change is obvious.
4. **One visual meaning per term, the same on every card:**

   | Term | How it is shown |
   |---|---|
   | Hypertrophy | Same cells, **bigger**, same number. Chip: "Bigger cells, same number" |
   | Hyperplasia | Cells **multiply**, same size. Chip: "More cells, same size" |
   | Dysplasia | Crowded, uneven cells with **large dark nuclei** (loss of polarity) above an intact basement membrane; red dashed box |
   | Metaplasia | An **orderly switch** to another normal cell type, with a strip of the old lining kept; blue dashed box |
   | Malignant spread | Cells travel along a vessel, or break through a dashed boundary with a red glow |
   | Immune cells | Servier B and T cells, macrophages and neutrophils; active cells glow, inactive ones turn grey with a dashed ghost |

5. **Labels.**
   - Use chips with leader lines (`R.callout`, `R.leader` + `R.chip`), size about 18 and at least 15 px.
   - Show at most about 4 labels on screen at once.
   - Labels must not overlap art or each other, or be cut off on phone or tablet.
   - Every visible shape is either obvious or labelled.
   - The answer chip is in red (green for "no cancer" or "beneficial") and sits in a consistent place.
6. **Motion.** Motion explains the mechanism: grow, multiply, switch, spread, attack, dock. Use eased timing and keep every step
   seekable. The first frame (t=0) already shows the scene.
7. **Medical accuracy.** Use only the source answer and explanation, plus certain textbook facts they imply. Never invent numbers or
   lab values; show "high" or "low" instead. If the book is wrong, the card avoids the error. For example, Q000009470's explanation
   calls chief cells "C-cells", so the card says only "chief cells".

## 4. Environment notes

- **Rendering.** If Playwright cannot find a browser, set
  `MOTIONCARDS_CHROMIUM=/opt/pw-browsers/chromium-1194/chrome-linux/chrome` (or `/opt/pw-browsers/chromium`).
- **Servier art.** Get it with
  `git clone --depth 1 --filter=blob:none --sparse https://github.com/duerrsimon/bioicons`, then
  `git sparse-checkout set static/icons/cc-by-3.0`. Raw GitHub URLs and the GitHub API may be blocked, but git works.
