# Watcher run (fired by the scheduled routine, or by the Head Department)

Goal: start a builder for every package whose images are all in Drive. Be cheap: when nothing is ready,
stop at step 2 without any other tool call or message.

1. Get the queue repo:
   `git clone -q --depth 1 -b claude/ai-biochemistry-image-generation-efl9y3 https://github.com/blsmohamme972-lab/Mcqs- /home/user/Mcqs- 2>/dev/null || git -C /home/user/Mcqs- pull -q`
2. `python3 /home/user/Mcqs-/kafu_queue/watch.py ready`
   If it prints `NONE`: end the session now. Say nothing. (`WAIT` lines are packages held back by the builder limit.)
3. Otherwise call `add_repo` (owner blsmohamme972-lab, repo Mcqs-, access "push"), then for each `READY <PKG>`:
   - `python3 kafu_queue/watch.py claim <PKG> "watcher <date>"`, commit `Claim <PKG>`, `git pull --rebase`, push.
     If the rebase shows someone else already claimed it, skip that package.
4. Start one builder per claimed package with `create_session` (never `send_message` to an old session: sessions do not
   take tasks from other sessions): title `Kafu lessons · <PKG>`, source_url `https://github.com/blsmohamme972-lab/MCQs-Mountain-`,
   source_revision = `lessons_base_branch` from config.json, tags `["kafu-lessons"]`, and as the prompt the exact output of
   `python3 kafu_queue/watch.py builder-prompt <PKG>`.
   - No `create_session`: use a one-shot `create_trigger` (run_once_at now + 2 minutes, create_new_session_on_fire true,
     notifications {"push": true}, initiation "human_schedule") with the same prompt.
   - Neither tool: build the first claimed package yourself by following that prompt, and release the others with
     `watch.py fail <PKG> "no builder tool; retry next run"`.
5. Check the builders you started earlier (`list_sessions` with tag `kafu-lessons`, `get_session`): a session with no update for
   20 minutes, or disconnected without a delivered ZIP, is stalled. `watch.py fail <PKG> "stalled"` and it is listed as `ready`
   again on the next run (a claim older than 3 hours is retried automatically).
6. End with one short Arabic line to the owner: which packages started building and which are stalled.
