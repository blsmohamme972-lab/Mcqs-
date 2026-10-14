# Building one package into an image-lesson ZIP (Claude builder session)

The full instructions are `BUILDER_TEMPLATE.md`, filled in for each package by:

    python3 kafu_queue/watch.py builder-prompt <PKG>

A builder's first message is that text. It already contains the rules learned from the GT chapter 4 run (2026-10-14):

- never end a turn waiting for a completion notice: schedule `send_later` and poll the log file;
- push the lesson JSONs before the slow voice build, send the ZIP as soon as `validate` passes (containers disappear);
- stop and report the refused command if a permission is denied, do not retry variations;
- commit only `lessons/<QID>.lesson.json` and `selection.json` by exact path, and put `work/` and `dist/` in `.git/info/exclude`;
- no messages to other sessions; one package per session; the voice engine is Breeze.

After the ZIP is delivered the Head Department marks the ledger (`watch.py deliver <PKG> "<note>"`).
