# Trial 09: full-q6-cfg4-20steps-768

Settings: full (non-turbo) Qwen-Image, Q6_K, 768x768, 20 steps, cfg 4.0, seed 42, prompt P1, offload on, cache auto. No overrides, no failures, no repairs.
- Total run: 133.7 min (setup 9.5 min, smoke 10 min, full run 8022 s)
- Sampling 7831 s (~391 s/step), VAE decode 150 s
- Peak RAM: 11976 MB (smoke 11971 MB)
- status.json "step" shows 15/16 (9.59s/step), which is the smoke-test line, not the main run.

Scores (/10):
- Composition: 6. Three clear zones (face / vein-to-skull / cave + eye), but the faces are ghosted and duplicated, with a lot of empty white space.
- Text accuracy: 7. Labels are spelled correctly: Infected facial lesion, Valveless veins, Cavernous Sinus, Carotid artery, Pulsating proptosis, Ocular pain, Fever, Chemosis. The nerve tags (CN III, IV, V, V2, V1) are tiny and jumbled, with a stray "V".
- Medical accuracy: 6. Danger-triangle lesion, bacteria in a vein, cave with a clot, carotid, nerve tags, eyes, thermometer and chemosis are all present. The nerve labelling is muddled, and the proptosis is only shown as an eye icon, not a bulging eye.
- Style: 6. Clean and friendly, nothing gory, but the faint faces look washed out and the skull is slightly odd.

Change: lower the cfg a little or add negative-prompt terms against duplicated or ghost faces, and make the cranial-nerve labels larger or fewer. Four times the cost of the turbo trials bought only a modest quality gain here.
