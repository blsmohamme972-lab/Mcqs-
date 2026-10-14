# Trial 07: turbo-q6-768-text-rich
Settings: prompt P3, seed 42, turbo LoRA, Q6_K, 768x768, 8 steps, cfg 1.0, offload on, cache auto. No overrides, no failures, run_trial.py unchanged.
- Setup (build + download): 12.9 min; run: 47.5 min (2851 s); total about 60 min
- Sampling 2552 s (about 16 s/step as logged, 16 steps reported); VAE decode 246 s
- Peak RAM: 12866 MB

## Image check
- Present: danger-triangle face with red zone and warning sign, infected lesion, Staph aureus, angular/ophthalmic veins with "No valves" and bacteria clusters travelling to a cave, cavernous sinus sign with purple thrombosis, nerves, internal carotid artery, bulging eye with spring (pulsating proptosis), chemosis, ocular pain, fever.
- Text is mostly spelled correctly. Nerve labels (CN III/IV/V1/V2/VI) are illegible scribbles; "Answer: Cavernous sinus" lowercase s; the pulse line is a small touch.
- Not gory. Chemosis is shown as a pale halo, not clearly swollen conjunctiva.

## Scores (/10)
- Composition: 8
- Text accuracy: 7 (nerve labels garbled)
- Medical accuracy: 7 (nerves unlabelled, carotid shown but not within sinus)
- Style: 8

## Next
Cut the nerve labels from the prompt or enlarge them as a single labelled bundle, and make the chemosis a clearly swollen eyelid ring. Text was good enough at 768 px that a lower step count may suffice.
