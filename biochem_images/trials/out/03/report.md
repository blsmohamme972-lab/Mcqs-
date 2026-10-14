# Trial 03 report: turbo-q5-768-no-offload

Settings: prompt P1, seed 42, turbo LoRA, quant Q5_0, 768x768, 8 steps, cfg 1.0, offload OFF, cache auto.
Purpose: is --offload-to-cpu useless on a CPU-only box? Compare peak RSS.

- State: done, exit code 0, no failures, no repairs, run_trial.py unchanged.
- Setup (build + download): 6.3 min; smoke test 600 s (smoke peak 11964 MB)
- Full run: 3011 s (50.2 min); sampling 2837 s, VAE decode 140 s
- Seconds per step: about 9.3 s/step (status.json, reported over 16 steps)
- Peak RAM: 11978 MB (about the same as smoke, about 12 GB of 15 GB)

Scores (/10):
- Composition: 7 (clear left-to-right flow lesion -> vein slide -> cave -> eye; a bit crowded)
- Text accuracy: 5 ("Ocular pain", "Cavernous sinus", "Valveless veins" OK; "Chemosis" duplicated; "Carotid artery" cut off; "CN III IV" / "V1 V2 VI" labels crude)
- Medical accuracy: 7 (danger-triangle lesion, bacteria in veins, clot in cave, CN fibres, carotid, proptosis, chemosis, fever thermometer all present; skull is a bit odd)
- Style: 7 (clean cartoon, not gory; some messy red hatching)

Change: fix text by shortening labels or using the larger/full-model trials, and avoid duplicate labels in the prompt (ask for one "Chemosis" label). Offload-off peaked at ~12 GB, so compare against the offload-on trials for the memory question.
