# Cavernous sinus mnemonic: 10 settings compared

Same story, Qwen-Image 2.1 on CPU (4 cores, 15 GB RAM), seed 42. Images: `out/NN/image.png`, overview: `contact_sheet.png`.
Scores are the leader's after viewing each image (10 = best); "text" is spelling/legibility of the labels.

| # | Settings | Image run | Peak RAM | Picmonic style | Text | Medical content | Verdict |
|---|---|---|---|---|---|---|---|
| 07 | Turbo Q6 768, text-rich prompt | 48 min | 12.9 GB | 7 | 7 | 8 | Best teaching poster (title, danger triangle, staph, angular/ophthalmic vein, no valves, answer banner). Nerve tags garbled. |
| 04 | Turbo Q6 1024 | 61 min | 12.8 GB | 9 | 6 | 7 | Best cartoon (angry staph, water slide, eye on a spring). "Pulsating Chemosis" mislabel, two caves, nerve tags garbled. |
| 06 | Turbo Q6 768, no text | 36 min | 12.8 GB | 8 | n/a | 7 | Cleanest pure picture; add labels yourself. |
| 01 | Turbo Q6 768 (baseline) | 33 min | 12.9 GB | 8 | 5 | 6 | Good, fastest decent result. |
| 03 | Turbo Q5_0 768, no `--offload-to-cpu` | 50 min | 12.0 GB | 7 | 5 | 7 | Duplicate "Chemosis", cut-off "Carotid artery". |
| 05 | Turbo Q6 1280x720 (16:9) | 78 min | 12.9 GB | 7 | 6 | 7 | Slide-shaped but elements small; empty margins. |
| 02 | Turbo Q4_K 768 | 36 min | 11.1 GB | 7 | 5 | 6 | Lowest RAM of the Turbo runs, slightly weaker. |
| 09 | Full Q6, CFG 4, 20 steps, 768 | 134 min | 12.0 GB | 4 | 6 | 6 | Worse than Turbo: ghosted, duplicated faces. |
| 08 | Full Q4_K, CFG 4, 12 steps, 768 | 81 min | 10.3 GB | 3 | 3 | 5 | Faint, sparse, ghost faces. |
| 10 | Full Q6, CFG 4, 12 steps, 1024 | 158 min | 11.9 GB | 2 | 2 | 3 | Failed: stray eyes everywhere, label misspelled ("CAVERICUS SINUS"). |

## Findings

- **Every setting fit in RAM** (10.3 to 12.9 GB of 15 GB), including 1024 px and CFG. The earlier out-of-memory kill is fixed by `--mmap`, text encoder on disk and VAE tiling.
- **The "expensive" settings were worse, not better.** Full model + CFG 4 + negative prompt (08, 09, 10) produced ghosted faces and stray eyes at 2 to 5 times the time of Turbo. Not tested: other CFG values (the engine docs use 6), no negative prompt, a flow-shift change. So this says "CFG 4 with this prompt does not work", not "the full model is worse".
- **Resolution helped (04 vs 01):** 1024 px gave larger, cleaner characters for about twice the time.
- **`--offload-to-cpu` has no measurable effect** on a CPU-only box (03: 12.0 GB, between Q4_K 11.1 and Q6 12.9, as the weights alone predict).
- **Q4_K saves about 1.8 GB** with a small quality loss.
- **Text is the weak point in every image.** Short labels are fine; the cranial-nerve tags ("CN III IV V1 V2 VI") are garbled in all of them. Draw nerves with colors and add that label by hand.
- **Run times were 2 to 3 times shorter than predicted** (turbo 768: 33 to 50 min).

## Recommendation

Turbo Q6 at 768 or 1024 with a short prompt; keep each label to 1 to 3 words and leave out the nerve list.
