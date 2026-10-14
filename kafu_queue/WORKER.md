# Building one package into an image-lesson ZIP (Claude worker session)

Your first message names the package `<PKG>`. It is already claimed in `kafu_queue/ledger.json`.
Work in one pass; send the owner one short Arabic message at the end. Do not wait for replies.

## Setup

1. Repos (call `add_repo` with access "push" for both; clone into /home/user):
   - `blsmohamme972-lab/Mcqs-` branch `claude/ai-biochemistry-image-generation-efl9y3` (queue, ledger, export)
   - `blsmohamme972-lab/MCQs-Mountain-` default branch (the lesson builder)
   If push to MCQs-Mountain- is refused, still build and send the ZIP; skip only its commit/PR and say so.
2. In MCQs-Mountain- start the voice setup in the background now (step 1 of `motioncards/LESSON_PROMPT.md`,
   chained with nothing else yet).

## Build

Follow `motioncards/LESSON_PROMPT.md` in MCQs-Mountain-, with these answers filled in:

- CHAPTER: from `kafu_queue/queue/<PKG>.json` (`book_id`, `chapter_id`), only the QIDs listed there.
- PACKAGE ID: `<PKG>`. Workspace `work/<PKG>`, ZIP `dist/MCARDS_<PKG>_r1.zip`.
- ALREADY LIVE: the package's `already_live` (true = yes).
- VOICE ENGINE: breeze (the owner chose it for this system; do not ask).
- EXPORT: copy `kafu_queue/<export>` from the package file to `work/input/` in MCQs-Mountain-.
- IMAGES: instead of attachments, run
  `python3 /home/user/Mcqs-/kafu_queue/watch.py download <PKG> work/<PKG>/lessons`
  (it saves `<QID>.png` from the shared Drive folder).
- Check each image's `Answer -->` against the key (LESSON_PROMPT step 3). A wrong or broken image: leave that
  QID out of this build, list it in your final message, and do not mark the package failed for it.

## Finish

1. Send the ZIP with SendUserFile, status "proactive", caption: `<PKG>: N lessons, ready for @KafuMcqsbot`.
2. MCQs-Mountain-: commit only lesson JSONs + selection.json on branch `lessons/<pkg in lower case>`, push,
   open a PR (LESSON_PROMPT step 8).
3. Mcqs-: `python3 kafu_queue/watch.py deliver <PKG> "<N lessons, PR link>"`, commit, `git pull --rebase`, push.
4. If the build cannot be fixed (LESSON_PROMPT step 7), run `watch.py fail <PKG> "<one-line reason>"`, commit,
   push, and tell the owner the reason in one line. A failed package is retried on a later run.
