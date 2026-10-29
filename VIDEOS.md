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

Tests: `for t in tools/tests/test_*.py; do python3 -m unittest $t; done`
