# Kafu image-lesson queue: ChatGPT draws, Claude narrates

```
owner: chapter export ──► Claude: queue/<PKG>.json + .md (one image prompt per question)
ChatGPT: reads queue/<PKG>.md ──► draws ──► saves <QID>.png to the Drive folder "Books"
routine (every 2 h): watch.py ready ──► package complete? ──► one builder session per package
builder: Drive images + export ──► MCQs-Mountain- LESSON_PROMPT.md (Breeze) ──► ZIP to the owner's phone
owner: forwards the ZIP to @KafuMcqsbot ──► live in the app
```

| File | For | What |
|---|---|---|
| `QUEUE_BUILDER.md` | Claude | export ──► packages and image prompts |
| `GPT.md` | ChatGPT | draw each prompt, save as `<QID>.png` in Drive |
| `WATCHER.md` | routine | find complete packages, start builders |
| `WORKER.md` | builder session | build, send the ZIP, open the PR, update the ledger |
| `watch.py` | all | Drive listing, `ready`, `status`, `download`, ledger states |
| `make_queue.py` | Claude | `split`, `render`, `check` |
| `ledger.json` | all | building / delivered / failed per package |

Status at any time: `python3 kafu_queue/watch.py status`.

Notes:
- The Drive folder is read through its "anyone with the link" view; keep that sharing on.
- This repository is public, so queue pages and exports here are public (owner's choice, 2026-10-14).
- Voice engine for this system: Breeze rotation (owner's choice, 2026-10-14).
