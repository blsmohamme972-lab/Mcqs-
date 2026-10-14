# Trial 04 report: turbo-q6-1024

**Settings:** prompt P1, seed 42, turbo LoRA, Q6_K, 1024x1024, 8 steps, cfg 1.0, offload on, cache q8_0, smoke test on.
**Result:** state done, exit code 0, no failures, no repairs, run_trial.py unchanged.
- Setup 6.1 min, smoke test 700 s, full run 3631 s (60.5 min), total 60.3 min per status.json.
- Sampling 3388 s = about 7.7 s/step (status shows 7.69 s/step on the last step); decode 207 s.
- Peak RAM 12818 MB (smoke test 12739 MB).

**Image check**
- Face: infected lesion in a red danger-triangle on the nose area, yellow bacteria. Good.
- Bacteria ride a water slide into the cave, "Valveless veins" label. Good.
- Cave labelled "CAVERNOUS SINUS" with a purple clot, a red carotid artery and 5 coloured nerve tags. Tags are garbled ("CN IV", "III V", "V1 V2", "V2 VI"). Nerves III, IV, V1, V2, VI are not clearly legible.
- Eye: bulging, red, with a spring (pulsating proptosis) and a puffy chemosis cuff; thermometer for fever and a lightning bolt for ocular pain. Good.
- Text errors: "Pulsating Chemosis" is a wrong label (the eye should show chemosis, not a second "pulsating"). The other labels are spelled correctly. "Ocular pain" and "Fever" are correct.
- Nothing scary or gory (the skull is cartoonish).

**Scores (out of 10)**
- Composition: 8
- Text accuracy: 6
- Medical accuracy: 7
- Style: 8

**What I would change:** drop the numbered nerve tags, or make them larger one-line labels, and reword the prompt so the chemosis label does not repeat "pulsating". The 60 min run at 1024 is well within budget, so a higher step count could be tried for cleaner text.
