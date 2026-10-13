# Worker instructions: one image trial

You are worker NN of 10 in an overnight experiment: the same medical visual
mnemonic generated with 10 different settings on Qwen-Image 2.1 (CPU only,
4 cores, 15 GB RAM). Your trial number is in your first message. Your job:
produce ONE image with your trial's settings, check it, write a report, push.
Nothing else. Be economical: short messages, no narration, no polling.

All paths below are relative to the repository root.
Settings: `biochem_images/trials/trials.json` (entry NN). Prompts: `biochem_images/trials/prompts/`.

## 1. Start (one command)

    python3 biochem_images/trials/run_trial.py NN --detach

It builds the engine, downloads the weights (10 to 20 GB, 10 to 20 min), runs a
1-step smoke test at your size, then the full run, and survives your session going
quiet. Progress and result are in `biochem_images/trials/out/NN/status.json`
(`"state"`: setup, smoke, running, done, failed). Expected total time is `est_hours` in trials.json.

## 2. Wait cheaply (this is where the budget goes)

Do NOT poll with sleep loops in the foreground and do NOT keep checking. Start ONE
background command and do nothing else until it finishes:

    until grep -qE '"state": "(done|failed)"' biochem_images/trials/out/NN/status.json 2>/dev/null; do sleep 60; done

(Bash with run_in_background true, timeout 7200000.) When it ends: if the state is
still not done/failed (the 2 h limit hit), start the same wait again. Read
status.json once per wake-up, not more. Never start a second run while one is active.

## 3. If the state is `failed`

Read `log_tail` in status.json (and `out/NN/smoke.log` or `run.log`). At most 3 repair
attempts in total. Fix the cause, then rerun the same command:

| Cause | Fix (use `--set`, it is remembered in out/NN/overrides.json) |
|---|---|
| `oom: true` or exit code -9/137 | first `--set cache=off`; then `--set quant=Q4_K`; then lower the size 25% (`W=` `H=`, multiples of 32). Say in the report exactly what you changed. |
| download or network error | just rerun (downloads resume) |
| unknown flag / argument error | read `sd-cli --help`, fix `build_cmd` in run_trial.py, rerun |
| build error | read the cmake output in runner.log, fix, rerun |

Anything else: read the log, think, fix the smallest thing. If after 3 attempts it
still fails, stop retrying: write the report with the failure, the log tail and your
diagnosis, and push that.

## 4. When the state is `done`

1. Open `biochem_images/trials/out/NN/image.png` with Read and judge it honestly.
   Facts to check (the question: 35-year-old woman, untreated infected facial lesion,
   ocular pain, fever, chemosis, pulsating proptosis -> cavernous sinus):
   - infected lesion on the face (danger triangle), bacteria travelling by valveless veins
   - cave / cavernous sinus with a clot; cranial nerves III, IV, V1, V2, VI and the carotid artery
   - bulging eye (proptosis), swollen conjunctiva (chemosis), fever, eye pain
   - every written label spelled correctly; no extra or duplicated characters; nothing scary/gory
2. Write `biochem_images/trials/out/NN/report.md` (under 25 lines): the settings, from
   status.json and result.json: total minutes, seconds per step, peak RAM in MB, any
   failure and fix; then a score out of 10 for each of: composition, text accuracy,
   medical accuracy, style; then 2 sentences on what you would change.
3. Delete `smoke.png` (keep `image.png`, `report.md`, `result.json`, `status.json`,
   `overrides.json` if present, `run.log`).
4. Commit and push. Your branch is already set up for you:

       git add biochem_images/trials/out/NN
       git commit -m "Trial NN result" && git push -u origin HEAD

   If the push is rejected, `git pull --rebase` and push again. Only touch your own
   `out/NN` folder (plus run_trial.py if you had to fix it; say so in the report).
5. Reply with at most 5 lines: state, total time, peak RAM, score, anything the leader must know. Then stop.

## Rules

- Do not change the prompt files or trials.json. Do not start other work.
- Never leave a run unattended without the wait command above; a finished run with no push is a failed trial.
- Do not use `sleep` in the foreground, and do not use any tool just to "check on" progress.
