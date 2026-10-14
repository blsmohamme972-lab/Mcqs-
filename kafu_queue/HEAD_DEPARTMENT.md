# Head Department: handoff (2026-10-14)

You are the main session ("Head Department") of the Kafu image-lesson system. The owner talks to you in
Arabic (Iraqi dialect). Reply in short Arabic. Read this whole file, then `README.md`, `GPT.md`,
`QUEUE_BUILDER.md`, `WATCHER.md` and `WORKER.md` in this folder before acting.

## The system (built and pushed)

1. Owner sends a chapter export (`kafu_mcq_text_export` JSON) → Head Department splits it into packages of
   8-10 questions and writes one image prompt per question (`QUEUE_BUILDER.md`, `make_queue.py`).
2. ChatGPT draws each image and saves it itself to the owner's Google Drive folder "Books" as `<QID>.png`
   (folder id `1A2_GAFmrM-EugAztWI6FgqbAuvXZWNSU`, public link; reading needs no connector:
   `python3 kafu_queue/watch.py status`).
3. Watcher routine `trig_01HYVKmcEmyumT8fgxKC8vjW` (every 2 hours at :58, fires into a new session, follows
   `WATCHER.md`) runs `watch.py ready`, claims complete packages in `ledger.json` and starts one builder per
   package (`create_session`, or a one-shot `create_trigger` fallback).
4. Builder (`WORKER.md`) builds the lesson with MCQs-Mountain `motioncards/LESSON_PROMPT.md` (Breeze voice
   rotation), sends the ZIP to the owner's phone (`SendUserFile`, proactive), opens the lesson PR on
   MCQs-Mountain branch `lessons/<pkg>` as LESSON_PROMPT step 8 says, and marks `watch.py deliver`.
5. The owner reviews the ZIP and forwards it to the Telegram bot @KafuMcqsbot himself (only the owner's
   Telegram id can upload). Never try to upload to the app yourself.

Not yet proven end to end: the watcher actually starting builders, and a builder finishing a full lesson.
Watch the first real run closely and fix `WATCHER.md` / `WORKER.md` if something breaks.

## Current batch: Get Through MRCS Part A, chapter 4 "Applied surgical anatomy — Lower Limb"

35 questions, Q155-189, QIDs `Q000006495`-`Q000006529`. Export: `exports/GET-THROUGH-MRCS-A-SBA-ch4.export.json`.
Packages (prompts all written, `make_queue.py check` OK):

| Package | QIDs |
|---|---|
| GT-CH4-Q155-163 | 6495-6503 (9) |
| GT-CH4-Q164-172 | 6504-6512 (9) |
| GT-CH4-Q173-181 | 6513-6521 (9) |
| GT-CH4-Q182-189 | 6522-6529 (8) |

State right now: **Drive folder is empty (0/35)**. The owner deleted every image from earlier attempts
(including Q155, Q156) and is regenerating all 35 in 7 parallel ChatGPT chats, 5 QIDs each:

- G1 6495-6499 · G2 6500-6504 · G3 6505-6509 · G4 6510-6514 · G5 6515-6519 · G6 6520-6524 · G7 6525-6529

Each prompt tells ChatGPT to read the package page `queue/<PKG>.md` (raw GitHub link), and for each of its
QIDs: skip it if `<QID>.png` is already in "Books", otherwise generate the image in the same message and save
it to Drive (one message "generate then save, do not stop after step 1" works, about 4 min per image).
Each prompt starts with this header, because ChatGPT kept pointing at old deleted images:

```
IMPORTANT - FRESH START: I deleted every image from earlier attempts. Ignore any images, files or results from previous chats or from your memory. Do not reuse, link to or re-upload any old image. The ONLY truth is what is in the Drive folder "Books" right now (not the trash): skip a QID only if <QID>.png is listed there now. Every image in this task must be newly generated in this chat.
```

Advice already given: empty the Drive trash, use brand-new chats (or Temporary Chat / memory off).

When the owner says "check" / "شيك": run `python3 kafu_queue/watch.py status`, report per package
`n/N` and which QIDs are missing, and flag duplicates or wrong names. If a package is complete you may
start its builder now instead of waiting for the routine (claim first, per `WATCHER.md`).

## Lessons learned about ChatGPT

- Old chat context makes it redraw old topics (it once drew cavernous sinus instead of Q155): always a new chat.
- Its GitHub tool can read repo text but cannot upload binary PNGs → that is why images go to Drive.
- Sometimes it stops after generating; a follow-up "save it now" fixes it.
- Our Google Drive connector is installed but not connected: we can only READ the public folder, not write.

## Corrections

`corrections/Q000006510.json`: Q170 stem was wrong (asked for the incorrect statement but only one was true).
Stem now asks "...which statement is correct?", key B unchanged, explanation extended. The owner must apply it
in the app (question text is not in any repo we can edit).

## Owner's rules (always)

- Facts only from stem, answer, explanation. Never change an answer key.
- Voice: Breeze rotation for this system.
- MCQs-Mountain lean storage: commit only `lesson.json` + `selection.json`; never images, audio, scenes, ZIPs.
- No PRs on this repo unless the owner asks. Work on branch `claude/ai-biochemistry-image-generation-efl9y3`.
- The Mcqs- repo is public; the owner accepted that. Never put keys or secrets in chat or in the repo.
- Manual review stays: ZIP to phone, owner forwards to the bot.
- When the owner says stop, stop everything.

## Open decisions

- Image style: current prompts are Picmonic cartoon. The old GT ch1-2 lessons used a semi-realistic painterly
  metaphor style (castle/bridges scene, "Q11" in the top-left, parchment title, answer banner, about 2:1).
  The owner has not chosen; keep cartoon unless told.
- Next chapters: when the owner sends a new export, follow `QUEUE_BUILDER.md`.

## Other work in this repo (not active)

`biochem_images/` (Qwen-Image 2.1 on CPU experiments; GPT-Image is better), `slide_mnemonics/`
(slide → mnemonic poster pipeline). 10 idle "CS-Trial" sessions exist; archive only if the owner asks.

## Plan for opening more sessions

- Head Department (you): talks to the owner, builds queues, checks Drive, starts builders, fixes the system.
- Builders: one session per complete package, titled `Kafu lessons · <PKG>`, tag `kafu-lessons`, prompt
  `Build package <PKG>. Follow kafu_queue/WORKER.md exactly. It is already claimed.` At most 4 at once.
- Watcher routine: the safety net that does the same every 2 hours. If you start builders yourself, claim in
  the ledger first so the routine does not start a duplicate.
- Check on builders with `get_session` / `list_events`; if one fails, `watch.py fail <PKG> "<reason>"` so
  it is retried, and tell the owner in one line.
