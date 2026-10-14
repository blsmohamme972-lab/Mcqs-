# Warm builder (one of 30 sessions): get ready, wait for images, build your own packages

You are builder SLOT <NN>. Your packages are listed under `slots["<NN>"]` in `kafu_queue/assignments.json` (JSON: {"queue_branch":..., "slots":{"01":[...],...}}) (2-3 packages of 2 questions each, chapter 36).
The Head Department session collects your ZIPs from the owner's inbox. It cannot send you tasks: you read your list from the repo yourself.
Rules of BUILDER_TEMPLATE.md apply in full (read it first). Send one short Arabic message at the end. Never message other sessions.

RULES
- Never end a turn without a pending `send_later` while you still wait or build. A completion notice never arrives: poll the log (`tail -n 5`), no `pgrep -f` loops.
- Never run two Breeze jobs at once: build one package at a time.
- A refused tool call: do not retry variations. Stop and give the exact refused command in one line (Arabic).
- Never change an answer key. Commit only `lessons/<QID>.lesson.json` and `selection.json`, by exact path. Run `printf 'work/\ndist/\n' >> .git/info/exclude` first.
- Never push to the queue repo (Mcqs-). Only to the lessons repo (MCQs-Mountain-), branch `lessons/<pkg_lower>`.
- The ZIP must be <= 15 MB so its base64 fits the inbox upload (a 2-question package is far smaller). If bigger, say so and send it with SendUserFile only.

PHASE 1: SETUP (now, once)
1. Start the voice setup in the background, nothing chained to it: step 1 of motioncards/LESSON_PROMPT.md (a failed download: run it again, it resumes).
2. `add_repo` blsmohamme972-lab / MCQs-Mountain- with access "push". `git fetch origin main`.
3. `git clone -q -b ccr-969bfa9e-ymsm3i https://github.com/blsmohamme972-lab/Mcqs- /home/user/Mcqs-` (read only). Read kafu_queue/BUILDER_TEMPLATE.md, WORKER.md and your slot in assignments.json.
4. Read CLAUDE.md and motioncards/lib/lesson.py of MCQs-Mountain-. Copy /home/user/Mcqs-/kafu_queue/exports/GET-THROUGH-MRCS-A-SBA-ch36.export.json to work/input/.
5. When the voice setup has finished, tell nothing; go to phase 2.

PHASE 2: WAIT FOR IMAGES (poll, cheap)
Every check: `git -C /home/user/Mcqs- pull -q`, re-read `slots["<NN>"]` (the Head may change it), then
`python3 /home/user/Mcqs-/kafu_queue/watch.py status | grep -E "<your packages joined with |>"`.
A package is ready when its line shows `images N/N` (all present). Nothing ready: `send_later` delay_minutes 10, message "check images", end the turn. Stop checking after 10 hours and report what is still missing.

PHASE 3: BUILD (one ready package at a time, in the order they become ready)
1. `python3 /home/user/Mcqs-/kafu_queue/watch.py builder-prompt <PKG>` and follow that text exactly from BUILD and FINISH, with these changes:
   - SETUP 1 (voice) and 3 (clone) are already done: skip them. SETUP 2: `git checkout -b lessons/<pkg_lower> origin/main` from the MCQs-Mountain- checkout. SETUP 4: export is already in work/input/. SETUP 5 (images): run it.
   - Use the inbox URL written in that prompt.
2. After the ZIP is uploaded and sent, say nothing; go back to phase 2 for your next package.
3. When all your packages are delivered: final message, one line in Arabic: slot NN, packages done N of N, PR links, anything left out.
