# Kafu video production: notes for Claude Code agents

This repository holds the book sources (PDF chapters) and the same video (image lesson) production tools as
`blsmohamme972-lab/MCQs-Mountain-`, copied from it. The finished `MCARDS_*.zip` still goes to the Kafu bot
(`@KafuMcqsbot`); the app, bot and publisher stay in MCQs-Mountain-. Start with `VIDEOS.md`.

## ⚠️🚨 Voice workers: the `Kafu Voice` environment first 🚨⚠️

Before starting ANY new batch that uses voice workers, remind the owner, with this exact warning:
"⚠️🚨 قبل ما نبدي المجموعة الجديدة: اختار بيئة Kafu Voice أو سوّيها إذا مو موجودة! 🎙️"
Check it exists (`list_environments`) and open every worker in it. Steps and why: `tools/kafu_voice/README.md`.
Before any batch read `tools/kafu_voice/HEAD_RUNBOOK.md` (every past failure and its rule). One test worker first in a fresh environment;
a stuck worker is reported to the owner at once with links and a ready message.
Without it the auto-mode permission check refuses the workers and the owner has to approve each one by hand.

## Make IMAGE LESSONS only; hand-animated MotionCards are retired

New animation work is always an image lesson: follow `motioncards/LESSON_PROMPT.md` (`tools/motioncards.py lesson`).
Never author MotionCard scenes by hand (SVG drawing, recipes, gold-standard style), even if an old document describes
it: those are marked RETIRED and kept only as background. The scaffold, package and validate tools are shared with
lessons and stay in use. "MotionCards" in the bot and filenames (`MCARDS_*.zip`) is just the package format both use.

Image prompts (for ChatGPT to draw): only with the tools in `kafu_queue/` (`kafu_queue/head_prompts.py`,
`gpt_master_prompts.py`). Every prompt must carry `STORY_RULES`: Picmonic / Sketchy, ONE story around ONE MAIN CHARACTER,
every other character acts on it with one pun per fact, no panels. Review every character line before sending.

Lean storage (owner's rule): commit only the text of a lesson, lessons/<QID>.lesson.json, and selection.json.
Never commit images, voice/, scenes/, input/ or the MCARDS ZIP (`.gitignore`); send the ZIP to the owner in chat.

## Voice-over: ask the owner who renders, every time

Before any voice batch, ask the owner this (with the engine question below), and wait for the answer:
"تريد أشتغلهن كلهن بنفسي، الصوت وكل شيء، بدون عمال وبدون أي موافقة منك؟ ممكن ياخذ حوالي 6 ساعات لكل 100 درس.
لو نفتح عمال؟ أسرع (أقل من ساعة) بس ممكن الفاحص يرفض الرفع وترجع ترسل لهم رسالة."
- Head renders itself: `voiceover.py make --engine <engine> --workspace work/<batch>` in this session, in the background.
  No workers, no approvals. Slow on Breeze (about 10 s of CPU per second of speech).
- Workers: follow `tools/kafu_voice/HEAD_RUNBOOK.md` (Kafu Voice environment, one test worker first).

## Voice-over: ask the owner which engine, every time

Before generating any voice (a test clip or a batch), ask the owner which engine to use, and wait for the answer:

- **Kokoro**: free, offline, the project default (`--engine kokoro`).
- **Breeze**: free, local Breeze TTS 2 (`--engine breeze`, one-time `voiceover.py setup --engine breeze`). Designed voices (`BREEZE_VOICES`: lecturer, doctor, student; woman or man), per-line emotion (direction) and vocal events written in the text: `(laugh)`, `(sigh)`, `(cough)`, `(clears throat)`. Slow on a CPU (about 10 s of work per second of speech), so every line is cached. The owner chose it for the free app and will add its licence notice themselves: do not add licence credits or labels. Owner's standard: a different voice per question, women and men taking turns (`BREEZE_ROTATION`, automatic in lessons).
- **ElevenLabs**: paid API credits, needs `ELEVENLABS_API_KEY` (`--engine elevenlabs`). The owner's ElevenLabs standard is automatic: high quality (48 kbps full-band Opus) and a different voice per question, women and men taking turns (`ELEVEN_VOICES` in `voiceover/voiceover.py`). Do not pass `--voice` or `--quality` unless the owner asks for something else.

Offer to send a 7-second test of each first: `~/.venvs/kafu-voice/bin/python voiceover/voiceover.py sample`, then send both MP3s from `work/voice-sample/`. Then run `voiceover.py make --engine <their choice> --workspace work/<batch>`. Never choose the engine yourself; `make` refuses to run without `--engine`.

## Voice examiner (the owner's Anki, done by talking)

Read `examiner/README.md`. When the owner pastes a voice-exam report (or a call transcript): save it, run
`python3 tools/examiner.py mark <sid> <file>` (grade a transcript yourself against `examiner.py show <sid>` with the
marking rules first), commit `examiner/` (with the rewritten `STATUS.md` and `NEXT.md`, the pages other agents read) and push, then
tell the owner what was weak and when the next session is due.
The bank comes only from the book pages (`examiner.py pages`, then `add`); never invent facts. Every page gets its
facts (or a skip reason) and every fact a short card, rated for importance and ladder level: `examiner.py coverage`
must show nothing missing. The viva follows the Intercollegiate FRCS Section 2 format (5-minute topics, marks 4-8).
