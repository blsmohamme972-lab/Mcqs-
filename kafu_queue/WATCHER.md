# Watcher run (fired by the scheduled routine every 2 hours)

Goal: start a builder for every package whose images are all in Drive. Be cheap: when nothing is ready,
stop at step 2 without any other tool call or message.

1. Get the queue repo:
   `git clone -q --depth 1 -b claude/ai-biochemistry-image-generation-efl9y3 https://github.com/blsmohamme972-lab/Mcqs- /home/user/Mcqs- 2>/dev/null || git -C /home/user/Mcqs- pull -q`
2. `python3 /home/user/Mcqs-/kafu_queue/watch.py ready`
   If it prints `NONE`: end the session now. Say nothing.
3. Otherwise call `add_repo` (owner blsmohamme972-lab, repo Mcqs-, access "push"), then for each `READY <PKG>`:
   - `python3 kafu_queue/watch.py claim <PKG> "watcher <date>"`, commit `Claim <PKG>`, `git pull --rebase`, push.
     If the rebase shows someone else already claimed it, skip that package.
4. Start a builder for each package you claimed (at most 4 per run; the rest wait for the next run):
   - If you have `create_session`: title `Kafu lessons · <PKG>`, source_url
     `https://github.com/blsmohamme972-lab/Mcqs-`, source_revision `claude/ai-biochemistry-image-generation-efl9y3`,
     tags `["kafu-lessons"]`, prompt: `Build package <PKG>. Follow kafu_queue/WORKER.md exactly. It is already claimed.`
   - Otherwise use `create_trigger` (one-shot): name `Kafu lessons <PKG>`, run_once_at = now + 2 minutes (UTC,
     RFC3339), create_new_session_on_fire true, notifications {"push": true}, initiation "human_schedule", prompt:
     `Build package <PKG>. First run: git clone -q -b claude/ai-biochemistry-image-generation-efl9y3 https://github.com/blsmohamme972-lab/Mcqs- /home/user/Mcqs- ; then follow /home/user/Mcqs-/kafu_queue/WORKER.md exactly. It is already claimed.`
   - If neither tool exists: build the first claimed package yourself by following WORKER.md, and release the
     others with `watch.py fail <PKG> "no builder tool; retry next run"` so the next run picks them up.
5. End with one short Arabic line to the owner: which packages started building.
