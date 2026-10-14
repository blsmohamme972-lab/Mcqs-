# Trial 05 report: turbo-q6-1280x720
Settings: prompt P1, seed 42, turbo LoRA, Q6_K, 1280x720, 8 steps, cfg 1.0, offload on, cache auto. No overrides.
- State: done, exit code 0, no failures, no repairs, run_trial.py untouched.
- Total: 77.7 min run (setup 8.3 min, smoke 1010 s, full run 4661 s).
- Sampling 4210 s = about 526 s/step over 8 steps (status log showed 17.24 s/step in the last progress line, which is the per-tile/sub-step rate); VAE decode 398 s.
- Peak RAM: 12897 MB (smoke 12878 MB).

Check:
- Face with infected lesion in a red warning triangle (danger triangle): yes. Bacteria on a blue water slide (valveless veins): yes.
- Cave with skull and cavernous sinus sign, purple clot, coloured nerves, carotid artery: yes.
- Bulging eye on a spring (pulsating proptosis), pink swollen conjunctiva (chemosis), fever thermometer, pain bolt: yes.
- Labels: "Pulsating proptosis", "Ocular pain", "Chemosis", "Fever", "Cavernous sinus", "Carotid artery", "Infected facial lesion", "Valveless veins" are correct. The cranial nerve label reads "CN IIII IV V1IVM", which is garbled.
- Not gory; friendly cartoon style.

Scores (/10): composition 8, text accuracy 6, medical accuracy 7, style 8.

Change: ask for the nerve label as separate short labels (CN III, CN IV, V1, V2, CN VI) or draw the nerves with colour keys instead of text. Also the lesion sits on the mouth/chin; ask for it near the nose or upper lip explicitly, and show the clot more clearly.
