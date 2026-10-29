# Video production (Kafu image lessons)

Copied from `blsmohamme972-lab/MCQs-Mountain-` so videos are made here the same way. Rules for agents: `CLAUDE.md`.

| What | Where |
|---|---|
| One session makes a chapter (prompt to paste) | `motioncards/LESSON_PROMPT.md` |
| Scaffold, lesson build, lint, package, validate | `tools/motioncards.py` (`motioncards/lib/`) |
| Voice-over (Kokoro, Breeze, ElevenLabs) | `voiceover/` (`voiceover/README.md`) |
| Voice workers | `tools/kafu_voice/` (`README.md`, `HEAD_RUNBOOK.md`) |
| Big runs: ChatGPT draws, Head + builder sessions narrate | `kafu_queue/` (`README.md`, `HEAD.md`, `BUILDER.md`, `OWNER_AR.md`) |

Flow: chapter export (from the Kafu bot) → image per question (ChatGPT, `kafu_queue/` prompts) → `tools/motioncards.py
scaffold` → `lessons/<QID>.lesson.json` → `tools/motioncards.py lesson` (voice) → `lint` → `package` → `validate` →
`MCARDS_<PACKAGE-ID>_r<N>.zip` sent to the owner in chat → owner uploads it to `@KafuMcqsbot`.

The app, bot and publisher are not here; they stay in MCQs-Mountain-. In `kafu_queue/`, `KAFU_MOUNTAIN` (the
project code for the checks) can point at this repository: everything the checks import (`motioncards/`) is here.

Only the method is here: no book exports, voice samples, art or past lessons. Each run brings its own export and images.

Tests: `python3 -m unittest tools/tests/test_lessons.py`

## Book lessons (explain our book, not MCQs)

The owner's direction: the image + voice lessons explain the **content of our book** (about one minute per topic), not
questions. They go to our app only, not to the Kafu bot, so there is no QID from the bot, no answer key and no question
fingerprint. Same engine (`motioncards/lib/lesson.py`: image, camera, voice track, entry HTML), different source and package:

| Step | Command |
|---|---|
| Topics of a chapter (text only, committed) | `booklessons/chapters/ch01.json` (18 topics, 100–135 words each) |
| One ChatGPT image prompt per topic | `python3 tools/booklessons.py prompts ch01` → `work/BOOK-CH01/prompts/<id>.txt` |
| Owner draws the pictures | save as `work/BOOK-CH01/images/<id>.png` (landscape 16:9) |
| Voice + scene (ask the engine question first) | `~/.venvs/kafu-voice/bin/python tools/booklessons.py build ch01 --engine breeze` |
| Package | `python3 tools/booklessons.py package ch01` → `BOOK-CH01_r1.zip` (`booklessons-manifest.json` + `entries/`) |

The app imports that zip (Reels feed + scene list, landscape player with the voice). Lean storage as before: commit only
text (`booklessons/`), never images, voice or zips. Topic ids `Q9<chapter 2><topic 2>0000` are only the engine's internal id.
Facts in the lesson text must come from the book page named in `pages`; check against the PDF before recording.
