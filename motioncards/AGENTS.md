# Agent instructions — Kafu MotionCards

> **RETIRED (Oct 2026). Do not use this to make new content.** The owner stopped hand-animated MotionCards.
> New work is IMAGE LESSONS only: follow `motioncards/LESSON_PROMPT.md`. This file is kept only as background for
> the shared scaffold/package/validate tools.

> **GOLD STANDARD (read first):** follow [`GOLD_STANDARD.md`](GOLD_STANDARD.md), the owner-approved workflow, card format and visual method from MRCS chapters 20–25.

> **SEPARATION WARNING:** Never modify, import, copy, rebrand, or depend on `Animations and illustrations/` (Medical Motion), DNAgens, or unrelated projects. MotionCards is a clean independent implementation.

## Development agents
- Read `PROJECT_BRIEF.md`, `MASTER_PROMPT.md`, and `HANDOFF.md` first.
- Inspect current main before continuing; preserve unrelated changes.
- Keep all new MotionCards namespaced as documented.
- Update `HANDOFF.md` after every meaningful milestone and before risky/long operations.
- Keep visual/infrastructure PRs open for owner review. Do not merge, apply production migrations, create production services or deploy without this project's owner approval.
- Exception approved by the owner: a **library proposal** (branch `library/…`, only `motioncards/library/` changed) merges automatically when `motioncards.py library-check` and the MotionCards tests pass in the `MotionCards library auto-merge` workflow. See "Improving the library" in `AUTHORING_V2.md`. Never try to get anything else merged through that path.
- Never test by operating the real book publish queue.
- Do not weaken existing book/export/download/sync/leaderboard/legacy tests.

## Content-generation agents
- Use the exported question objects exactly as supplied.
- Never rewrite questions, allocate QIDs, infer missing records, or change correct answers.
- Use only the requested/selected QIDs and recorded durations.
- Run the provided scaffold/preview/validate/package commands.
- Do not hand-type hashes or checksums; tooling generates them.
- If a figure is essential and its bytes were not inspected through the approved workflow, mark the item blocked.
- A blocked explicit QID is never silently substituted.

## Library improvement
- When you create a reusable drawing or animation that the library lacks and you used it in a real card, propose it as described in `AUTHORING_V2.md` ("Improving the library"). Propose only clear improvements; when in doubt, don't.

## Runtime rules
- Scene code is deterministic against one host-controlled timeline.
- No independent timers/CSS animation loops that ignore pause/seek.
- No eval/new Function, network dependencies, Telegram SDK or app credentials.
- Final panel derives its answer text from validated source data.
