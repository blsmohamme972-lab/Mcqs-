# Trial 10 report: full-q6-cfg4-12steps-1024
Settings: prompt P1, seed 42, Q6_K, 1024x1024, 12 steps (log shows 25 steps), cfg 4.0, offload on, cache q8_0, no turbo.
Result: state done, exit 0, no failures, no repairs.
- Total run: 157.5 min (setup 8 min, smoke 18.5 min, main run 9452 s)
- Sampling 9181 s, about 9.0 s/step in the last logged step (status showed ~774 s/step earlier in the run); decode 230 s
- Peak RAM: 11904 MB

Scores (out of 10):
- Composition: 3 (three sparse columns on white, many stray floating eyes, no clear story)
- Text accuracy: 3 (only label is "CAVERICUS SINUS", misspelled)
- Medical accuracy: 3 (danger-triangle on face, vein channel with bacteria, cave, clot, nerves and artery are shown; no proptosis, chemosis, fever or labelled nerves III/IV/V1/V2/VI)
- Style: 5 (clean, non-gory cartoon style, but cluttered with eyes)

Change: shorten the prompt and drop the repeated "eyes" wording, which produced the stray eyes, and render labels as short single words. Compose one single scene instead of three panels.
