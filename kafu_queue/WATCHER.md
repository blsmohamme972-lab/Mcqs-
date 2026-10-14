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
4. For each package you claimed, open a builder session with `create_session`:
   - title `Kafu lessons · <PKG>`
   - source_url `https://github.com/blsmohamme972-lab/Mcqs-`, source_revision
     `claude/ai-biochemistry-image-generation-efl9y3`
   - prompt: `Build package <PKG>. Follow kafu_queue/WORKER.md exactly. It is already claimed.`
   - tags `["kafu-lessons"]`
   At most 4 builders per run; the rest stay ready for the next run.
5. End with one short Arabic line to the owner: which packages started building.
