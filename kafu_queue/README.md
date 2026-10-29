# Kafu image lessons: ChatGPT writes and draws, Claude narrates

These tools live on branch `master` of this repository and are only READ during a run: nothing of a run is written to
GitHub (owner's rule). A run's data (exports, packages, ledger, voice scripts, slot split, settings) lives in the Head's data
folder (`kafu_data.py`, `bundle.py use`) and reaches the builders as one bundle file through the owner's inbox.

```
owner: export(s) ──► ChatGPT (master prompt) and ──► Head: preflight.py export ──► make_queue.py split-all (packages of 6)
ChatGPT: 8 questions per batch ──► painter_batchNN.html (one card = one message)
owner: each card ──► new ChatGPT chat ──► Drive folder: 8 × <QID>.png + VOICE_<first>-<last>.txt (9 things)
Head (at the same time): bundle.py pack ──► inbox ──► N builder sessions start at once (BUILDER.md, cheap model)
builder: autobuild.py in the background: voice_setup.py ──► for each package as soon as its images + voice are in Drive:
         scaffold ──► images ──► lesson_from_voice.py ──► Breeze ──► lint ──► package ──► validate ──► ZIP ──► session uploads it
Head (while drawing): watch.py missing, preflight.py sheet (every banner vs the key), voice_collect.py, collect the ZIPs
Head (end): collect_zips.py ──► preflight.py zips ──► merge_zips.py (≤ 15 MB) ──► preflight.py coverage ──► owner ──► @KafuMcqsbot
```

| File | For | What |
|---|---|---|
| `HEAD.md` | Head session | the runbook, stage by stage, and the table of past failures and their prevention |
| `OWNER_AR.md` | owner | the owner's part in Iraqi Arabic |
| `BUILDER.md` | builder sessions | template filled by `assign.py prompt NN --bundle ID` |
| `kafu_data.py` | all tools | where the run's data lives (never the repository) and the settings |
| `bundle.py` | Head, builders | `use` the data folder, `pack` it into one file for the inbox, `unpack` it in a builder |
| `gpt_writer.py` | Head | `--master`: the fixed ChatGPT prompt (owner attaches the exports); `--prefix`: prompts with the questions inside |
| `make_queue.py` | Head | `split` / `split-all` the exports into packages, `check` them |
| `preflight.py` | Head, builders | gates: `export`, `images`, `zips`, `coverage`; `sheet`: review sheets of every answer banner |
| `voice_collect.py` | Head | reads ChatGPT's `VOICE_*.txt` from Drive (or a painter page), checks them |
| `lesson_from_voice.py` | builders | turns a voice script + image into `<QID>.lesson.json` for review |
| `assign.py` | Head | `options` (time and money per session count), `resize` to exactly N equal packages, `split` one package per slot, `prompt` per slot, `left`; `--from Q` for a new run on the same prefix |
| `head_prompts.py` | Head | the Head's own image prompts: `check` them (banner = key, no wrong option, no invented number, evidence per character), `page` = the painter HTML for ChatGPT |
| `places_collect.py` | Head | ChatGPT's `places_*.txt` notes from Drive -> `picture_notes` in the packages, for the builders' voice |
| `autobuild.py` | builders | the whole build of a slot in one background job; `status` says what to upload; `uploaded`, `retry` |
| `voice_setup.py` | builders | Breeze setup that survives cut downloads (size-checked resume), then a 4-second test clip |
| `drive.py` | Head | `set LINK`: the owner's Drive folder; `show` |
| `watch.py` | all | Drive listing: `status`, `missing`, `get`, `download`; ledger: `state`, `deliver`, `fail` |
| `collect_zips.py` | Head | decode and check the base64 ZIPs downloaded from the inbox |
| `merge_zips.py` | Head | merge package ZIPs into parts of at most 9 MB for the bot (bigger parts failed on the phone) |
| `config.json` | all | defaults: Drive folder, inbox, package size, batch size, limits |

`exports/GET-THROUGH-MRCS-A-SBA-ch36.export.json` is the chapter 36 export (135 questions, already published) and serves as a
test fixture for the scripts.

Notes:
- The Drive folder is read through its "anyone with the link" view; keep that sharing on.
- No run data is stored in this repository; only the tools. The repository is public.
- Voice engine: Breeze rotation (owner's choice).
