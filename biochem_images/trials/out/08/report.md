# Trial 08 report
Settings: full-q4k-cfg4-12steps-768 — prompt P1, seed 42, Q4_K, 768x768, 12 steps, cfg 4.0, offload on, cache auto.
State: done, exit code 0, no failures, no repairs, run_trial.py unchanged.
Time: ~80.7 min total (setup 6.1 min, smoke 12 min, full run 80.8 min incl. decode).
Sampling 4563 s (~15.8 s/step per status), VAE decode 249 s. Peak RAM 10270 MB.

Image: left column shows a face with a red danger-triangle and yellow bacteria on the nose/lip;
a blue winding vein carries yellow bacteria down to a cave opening; the cavernous sinus sign with a
purple clot, coloured nerves and a red carotid artery; right column shows several bulging/red eyes,
swollen conjunctiva, a thermometer and a pain bolt. Friendly cartoon style, nothing gory.
Problems: small labels are garbled ("Valveless", "Chemosis", "Carotid artery", "Proptosis" are
mangled); nerve labels read "CN III / V / V1V2 / II" (incomplete, III/IV/VI not clear);
"CAVERNOUS SINUS" is correct. Composition is sparse with lots of empty space; faces are small and
repeated; no clear single patient.

Scores (/10): composition 5, text accuracy 4, medical accuracy 6, style 7.

Change: enlarge the scene to fill the canvas with fewer, larger elements and limit text to 2-3
short labels (CAVERNOUS SINUS, DANGER TRIANGLE) to avoid garbled small text. Add more steps or
raise resolution if time allows, since small labels degrade at 768 px.
