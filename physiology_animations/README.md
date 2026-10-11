# Physiology animation explainers

Ten 8-second animated explanations (1280×720, 30 fps, H.264), built on the diagrams in `My_Physiology_50`.

| # | Topic | Source diagram(s) |
|---|-------|-------------------|
| 1 | Cardiac conduction + ECG | heart-nodes-branches-fibers, electrocardiogram-ecg |
| 2 | Windkessel effect (aorta as a second pump) | systole, diastole |
| 3 | Mechanics of breathing (Boyle's law) | breathing-inspiration, breathing-expiration |
| 4 | Alveolar gas exchange | gas-exchange-pulmonary |
| 5 | Saltatory conduction | Motor_neuron |
| 6 | Skeletal muscle pump / venous return | venous-return-1 |
| 7 | Visual pathway & optic chiasm | optical-pathway |
| 8 | Absorption in the villus | intestinal-villi |
| 9 | Starling forces in a capillary | capillary |
| 10 | Nephron: filtrate to urine | nephron_2d |

- `physiology-10-explainers.mp4` — all ten back to back (80 s).
- `videos/` — the individual MP4s.
- `html/` — standalone looping versions (open in a browser).
- `source/` — engine, per-scene scripts, build and render scripts.
  - `node build.js <svgRoot> <outDir>` inlines the SVGs into HTML.
  - `node render.js <htmlDir> <videoDir> [prefix]` captures 240 frames per scene with Playwright and encodes with ffmpeg.
