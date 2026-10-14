# Trial 01 report: turbo-q6-768-baseline
Settings: prompt P1, seed 42, turbo LoRA, Q6_K, 768x768, 8 steps, cfg 1.0, offload on, cache auto.
- State: done, exit code 0, no failures, no overrides, run_trial.py unchanged.
- Total: setup 5.2 min, run 32.9 min (sampling 1806 s, decode 132 s).
- Speed: about 8.1 s/step (log shows 16 step counter for 8 steps; sampling 1806 s total).
- Peak RAM: 12863 MB.

Image check:
- Present: infected lesion in danger triangle, blue vein with bacteria, skull/eye, cave labelled CAVERNOUS SINUS, purple clot, nerves, red carotid, proptosis, chemosis, fever thermometer, pain bolt.
- Text problems: "CN III V" and the second nerve label are garbled; "Fever" has a stray character; "CAVERNOUS" is slightly odd; "Pulsating proptosis" is OK.
- Missing: IV, V1, V2, VI not legible. Not gory.

Scores (/10):
- Composition: 7
- Text accuracy: 5
- Medical accuracy: 6
- Style: 8

Change: drop the small nerve labels (or render nerves unlabeled, add labels in post) and raise steps or resolution to improve text; keep this layout.
