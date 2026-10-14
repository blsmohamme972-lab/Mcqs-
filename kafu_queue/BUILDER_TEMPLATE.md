Build Kafu image lessons for package PKG = {PKG}, QIDs: {QIDS} (questions {NUMBERS}; {CHAPTER}). The owner asked for this build.
One pass, no questions. Send one short Arabic message at the end. Do not message other sessions and do not wait for replies.

RULES THAT PREVENT THE KNOWN FAILURES (read first)
- Never end a turn "waiting for a completion notice": it does not arrive. While the voice build runs, call `send_later` (delay_minutes 5, message "check build log") before you end the turn, and check the log each time. If you stay in the turn, poll the log file (`tail -n 5 <log>`), never `pgrep -f` or a `while` loop that can match itself.
- Your container can disappear. Push the lesson JSONs as soon as they are written (before the voice build), and run SendUserFile the moment `validate` passes.
- If a tool call is refused by permissions, do not retry variations. Stop and give the exact command that was refused in one line (Arabic) as your final message.
- Commit and push only `lessons/<QID>.lesson.json` and `selection.json`, adding them by exact path (`git add work/{PKG}/lessons/Q....lesson.json work/{PKG}/selection.json`). Before anything else run `printf 'work/\ndist/\n' >> .git/info/exclude` so the stop hook never sees the scaffold folder.
- Never run two Breeze jobs at once. Voice engine is breeze (the owner chose it; do not ask).

SETUP
1. Start the voice setup now, in the background, with nothing else chained: step 1 of motioncards/LESSON_PROMPT.md (a failed model download: run it again, it resumes).
2. Call add_repo for {LESSONS_REPO_SLUG} (access "push"). `git fetch origin {BASE_BRANCH} && git checkout -b lessons/{pkg_lower} origin/{BASE_BRANCH}` (this branch has the intro: question box, answer box, word highlight).
3. `git clone -q -b {QUEUE_BRANCH} {QUEUE_REPO} /home/user/Mcqs-` (read only; never push to it).
4. Copy /home/user/Mcqs-/kafu_queue/{EXPORT} to work/input/.
5. Images (after scaffold, which may empty the folder): `python3 /home/user/Mcqs-/kafu_queue/watch.py get work/{PKG}/lessons {QIDS}`.

BUILD: follow motioncards/LESSON_PROMPT.md on that branch, steps 3-8, with:
- PACKAGE ID {PKG}, workspace work/{PKG}, ZIP dist/MCARDS_{PKG}_r1.zip, only these QIDs. ALREADY LIVE: {ALREADY_LIVE}. Voice engine breeze.
- Stem, options, key, explanation: from the export (also /home/user/Mcqs-/kafu_queue/queue/{PKG}.json). Facts only from them; never change the key. If the stem contradicts its key (asks for the incorrect statement but only one option is true, etc.), keep the key, write the intro question the way it must read to be correct, and list the QID in your final message and in the PR.
- Every lesson gets "question" (<=220 chars, short faithful version) and "answer" (<=110 chars, from the key). The intro word highlight uses faster-whisper; if the build prints "word timing without the recogniser", say so in the final message.
- Check each image's "Answer -->" against the key. A wrong or broken image: leave that QID out, name it, do not fail the package.

FINISH
- Right after `validate` passes, before SendUserFile: read the owner's ZIP inbox (Artifact action "read", url https://claude.ai/artifact/J5yRwS9degoyFckDzPTijN), then `base64 -w0 dist/MCARDS_{PKG}_r1.zip > dist/MCARDS_{PKG}_r1.zip.b64.txt` and upload it as an asset (Artifact action "publish", same url, asset true, file_path that .b64.txt file, only that one file in the call). If the upload fails, put the exact error in your final message and carry on.
- SendUserFile the ZIP, status "proactive", caption "{PKG}: N lessons, ready for @KafuMcqsbot".
- Open a PR on {LESSONS_REPO_SLUG}: head lessons/{pkg_lower}, base {BASE_BRANCH}, title "Lessons {PKG}"; list any QID whose explanation or stem you corrected.
- Final message, one short line in Arabic: N lessons, ZIP sent, PR link, word timing ok or fallback, any QID left out.
