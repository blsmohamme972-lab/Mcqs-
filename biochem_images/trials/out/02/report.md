# Trial 02 report: turbo-q4k-768
Settings: prompt P1, seed 42, Turbo LoRA, quant Q4_K, 768x768, 8 steps, cfg 1.0, offload on, cache auto. No overrides, no failures, run_trial.py unchanged.
Timing: setup 8.3 min, smoke 570 s, full run 2171 s (36.2 min); total elapsed 36.0 min per status.json (est 1.1 h).
Sampling 1892 s (about 15 s/step in the status line; 8 steps), VAE decode 245 s.
Peak RAM: 11132 MB (smoke 11123 MB).

Image: danger-triangle face with infected lesion, blue vein river carrying bacteria to a cave labelled CAVERNOUS SINUS with a purple clot, carotid artery, cranial nerve lines, bulging eye with spring (pulsating proptosis), chemosis, thermometer. Not gory.
Flaws: "premosis" (stray label, should be proptosis/chemosis), "Ocular pairn" (typo), CN labels garbled ("CN III" ok, others illegible), duplicate proptosis labels, no clear CN IV/V1/V2/VI.

Scores (/10):
- Composition: 7
- Text accuracy: 5
- Medical accuracy: 6
- Style: 7

Change: Keep Q4_K (fast, 11 GB) but cut label count in the prompt, or go to 1024 px, so text renders cleanly; spell out each cranial nerve label separately or draw them unlabelled.
