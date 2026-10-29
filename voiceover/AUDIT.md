# Golden 8 Rules audit (for a Claude Code agent)

Use this to re-check `voiceover/` against the Golden 8 Rules in `README.md`. Measure, don't assume: every verdict needs evidence (a command output, a number, a file and line, or a licence quote with a link).

## How to run the audit

1. Read `voiceover/README.md`, `DESIGN.md`, `PLATFORM_PLAN.md` and `NARRATION_GUIDE.md`, plus `motioncards/AGENTS.md`.
2. Set up and run everything:
   - `voiceover/bootstrap.sh`
   - `~/.venvs/kafu-voice/bin/python -m unittest voiceover/tests/test_voiceover.py voiceover/tests/test_voice_sync_browser.py`
   - `voiceover.py make --engine kokoro` on a copy of a real batch workspace (or the chapter 10 scenes)
3. Fill the table below with **PASS / PARTIAL / FAIL**, the evidence, and the fix.
4. Fix every FAIL and PARTIAL that can be fixed inside `voiceover/` (or the docs), re-run the checks, then report.
5. Anything that needs platform code (app, Workers, compiler, validator, bot): do **not** change it. Add it to `PLATFORM_PLAN.md` and list it in the report for the owner.

## Checklist

| # | Rule | Pass when… | Measure with |
|---|---|---|---|
| 1 | Best quality, smallest size, free | The voice model and every tool are free for commercial use (re-read their **own** licence files today). The voice is the best-rated one available. Average size ≤ 16 KB per 8 s card. `check` scores ≥ 0.85 on every beat. No better free option has appeared since (search the web; compare on quality, size, licence) | `ls -l work/*/voice/*.opus`, `check` output, licence links |
| 2 | Voice comes as a ZIP through the Telegram bot | The plan puts voice inside the normal `MCARDS_*.zip` (no separate upload path, no new bot command). Validator rules are specified | `PLATFORM_PLAN.md` PR 2 |
| 3 | Claude Code does all the work, the owner only uploads | No step needs the owner except uploading the ZIP: no accounts, keys, manual audio editing or listening required (review videos are optional) | Walk the README steps on a clean workspace |
| 4 | Cloudflare and the project stay free | No paid API or service anywhere. Voice adds 0 requests and 0 files on Cloudflare | `grep -ri "api_key\|token\|https://" voiceover/`, DESIGN §5 |
| 5 | Thousands of students daily on the free plan | Card views don't count toward the 100,000 Worker requests/day (or the plan to fix that exists and is first). Download added per card ≤ 20 KB | `motioncards-worker/wrangler.jsonc`, PLATFORM_PLAN PR 1 |
| 6 | 300+ books free | Total voice size for 300 books is estimated with today's numbers. The 20,000-files-per-Worker limit has a plan | DESIGN §6, PLATFORM_PLAN PR 4 |
| 7 | Voice synced with the animation | `check` onset error ≤ 80 ms on every beat. `synth` refuses lines that overrun their beat. The browser test shows < 60 ms drift through play, seek and pause | `check` output, the browser test |
| 8 | An agent can make the voice easily, least effort, highest quality | A fresh machine reaches DONE with `bootstrap.sh` + `make` only. `make` reports **all** problems in one pass, each with a clear fix. Docs say exactly what to edit | Time it on a clean workspace; count the edit passes needed |

## Report format

1. One table: rule, verdict, evidence, what you changed.
2. What still needs the owner (platform PRs, choices), with a recommendation for each.
3. Commit the fixes and open a PR. Never merge it, and never deploy.
