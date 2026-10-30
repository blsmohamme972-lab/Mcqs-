# Voice examiner: Anki, done by talking

Instead of flipping cards, you take an oral exam (a viva). ChatGPT or Claude is the examiner in a voice call, asks
you the book's questions one by one, and at the end writes a short report. `mark` turns that report into FSRS
spaced repetition: every card gets its next date from **how** you answered, not from a button you pressed.

بدل ما تقلب كروت: مكالمة صوتية مع GPT أو Claude كممتحن، يسألك من الكتاب، وبعد المكالمة التقرير يحدد مواعيد المراجعة.

## The loop

```
book pages ──(1) pages + add──> examiner/bank/chNN.json      Q&A cards (question, model answer, key points)
                                        │
                          (2) session ──┴──> examiner prompt: paste it in ChatGPT / Claude, start the voice call
                                                   │  you answer aloud; it hints, corrects, retries what you missed
                                                   ▼
                          (3) type REPORT ──> JSON report ──> paste it here (to Claude Code)
                                                   │
                          (4) mark ────────────────┴──> examiner/state.json: FSRS schedule, notes, leeches
```

1. **Pages to Q&A** (once per chunk of the book)
   - `python3 tools/examiner.py pages ch01 --pages 2-6` writes the page text plus the card-writing rules to
     `work/examiner/qa/ch01_p002-006.prompt.md`.
   - Claude (or ChatGPT) writes the cards from it, using only what is on those pages. Each card has a spoken question,
     a 1–3 sentence model answer, and 1–5 **key points** that must be said for full marks.
   - `python3 tools/examiner.py add ch01 cards.json` checks the cards and merges them into the bank.
2. **Plan the exam**
   - Run `python3 tools/examiner.py session --minutes 20` (add `--new 8` and `--chapters 1 2` if you like).
   - It writes `work/examiner/<sid>.prompt.md`. Paste that into a new ChatGPT or Claude chat and switch to voice.
3. **The call**
   - The examiner asks one question at a time.
   - If you're stuck it gives at most one hint, then a short correction.
   - Questions marked TEACH (ones you keep failing) are explained first and asked at the end.
   - Everything you missed is asked once more at the end.
   - Say "end exam" to stop early. Then type `REPORT` and copy the JSON it writes.
4. **Mark**
   - Paste the report here. Claude Code saves it and runs `python3 tools/examiner.py mark <sid> report.json`, then
     commits `examiner/`.
   - If the examiner forgot to write a report, paste the call's transcript instead. Claude grades it against
     `examiner.py show <sid>` using the same marking rules.

`python3 tools/examiner.py status` shows what is due now and this week, plus new and leech cards per chapter and
your weakest cards.

## How the marking is smart

| What the examiner saw | Rating |
|---|---|
| wrong, blank, under half the key points, or right only after 2 hints | Again |
| partial (half or more of the points), right after 1 hint, or a correct guess | Hard |
| right but hesitant, unsure, or not every point | Good |
| every key point, at once, no hint, sure | Easy |

- **Once failed, never Easy.** A card you have failed before gets at most Good, even when you're fluent.
- **Retries don't fool the schedule.** A correct answer to a retry later in the same call counts only as a same-day
  review, capped at Good. It shows short-term memory, not learning.
- **Failures spread to the whole idea.** When you fail a card, its siblings on the same page and its `related` cards
  are brought forward to tomorrow. Their memory model is unchanged.
- **Confident errors come first.** A wrong answer you said you were sure of is a dangerous misconception, so that
  card leads the next session.
- **Leeches are taught, not drilled.** After 4 failures a card is explained before it is asked. It leaves leech status
  once you get it right.
- **The examiner reads your last note.** Each card keeps the last notes ("mixed up class III and IV"), and the next
  examiner prompt tells the examiner to probe exactly that.
- **Sessions are ordered to help you remember.** Due cards come most-forgotten first. New cards come in book order,
  spread among the reviews, and two questions from the same page never come back to back.

FSRS-6 here is py-fsrs 6.3.2 (`pip install fsrs==6.3.2`), the same engine the app's `Fsrs.kt` is verified against.
It runs without learning steps, because a voice session is a day-scale event: every answer schedules in days.

## Files (all text, committed)

- `examiner/bank/chNN.json`: the cards, `{"chapter", "title", "cards": [...]}`. A card looks like this:
  `{"id": "ch01.p002.01", "chapter": 1, "page": 2, "topic", "type": recall|list|why|case|compare|value, "q", "a", "points": [...], "related": [...]}`.
  `page` is the printed book page.
- `examiner/state.json`: per card, the FSRS card, reps, lapses, history (every rating with its reason), notes and the
  leech flag. It also lists the marked sessions.
- `examiner/sessions/<sid>.plan.json` and `<sid>.report.json`: what was asked and what happened.
- `work/examiner/`: page text and examiner prompts. This folder is ignored, because it can be rebuilt.
