# Voice examiner: the board viva, done by talking

Instead of flipping cards, you sit an oral exam (a viva). ChatGPT or Claude plays the two examiners in a voice call
and runs it like the UK Intercollegiate FRCS (Cardiothoracic Surgery) Section 2 viva:
- 5-minute topics, with short questions that climb from knowledge to management;
- every topic marked 4 to 8, where 6 is a pass;
- no feedback until the debrief.

`mark` keeps the viva marks and turns every answer into FSRS spaced repetition. Each card's next date comes from how
you answered, not from a button you pressed.

The book is covered completely: every page is broken into its facts, and every fact is tested by at least one short
card. Importance decides what you meet first, never what is left out.

بدل الكروت: امتحان شفهي بمكالمة صوتية مع GPT أو Claude، بنفس شكل امتحان البورد البريطاني (FRCS). مواضيع كل واحد
خمس دقائق، وأسئلة قصيرة تصعد من المعرفة إلى التدبير. كل موضوع ياخذ درجة من 4 إلى 8 والنجاح 6. كل معلومة بالكتاب
لها سؤال، والأهمية تحدد الترتيب فقط، يعني ما تنحذف أي معلومة.

## The loop

```
book pages ─(1) pages + add─> examiner/bank/chNN.json   page facts + short cards (importance, ladder level)
                                     │                    coverage: every page done, every fact tested
                        (2) session ─┴─> examiner prompt: paste it in ChatGPT / Claude, start the voice call
                                              │  two examiners, 5-minute topics, no feedback until the debrief
                                              ▼
                        (3) type REPORT ──> JSON report (a mark per topic, a row per question) ──> paste it here
                                              │
                        (4) mark ─────────────┴─> examiner/state.json: viva marks, FSRS schedule, notes, leeches
```

1. **Pages to the bank.** Do this once per chunk of the book, until the whole book is done.
   - `python3 tools/examiner.py pages ch01 --pages 2-6` writes the page text plus the bank-writing rules to
     `work/examiner/qa/ch01_p002-006.prompt.md`.
   - Claude (or ChatGPT) writes the bank from it in two steps:
     - **Facts:** every examinable statement on every page, in page order (or a reason to skip the page).
     - **Cards:** short viva questions until every fact is tested. Each card has its importance and its rung on the ladder.
   - `python3 tools/examiner.py add ch01 bank.json` checks everything, merges it, and prints the tier shares and the coverage.
   - `python3 tools/examiner.py coverage` lists, for each chapter, the pages still to write and the facts no card tests.
     Nothing counts as done until both lists are empty.
2. **Plan a viva.**
   - `python3 tools/examiner.py session` plans a full viva: 6 topics, 30 minutes.
   - Options:
     - `--topics 3` for a short one.
     - `--viva cardiac` (or `critical`, `congenital`, `thoracic`) for one of the four vivas; `--chapters 7` for one chapter.
       By default the scope is the whole book.
     - `--tier A` to start new cards only from the must-know ones.
     - `--mode practice` for feedback after every answer.
   - It writes `work/examiner/<sid>.prompt.md`. Paste that into a new ChatGPT or Claude chat and switch to voice.
3. **The viva.**
   - Examiner 1 takes the first half of the topics, Examiner 2 the rest.
   - Each topic is named, then climbed: L1 knowledge, L2 understanding, L3 management, L4 complications and evidence.
   - Questions are short and asked one at a time. Examiners may prompt ("anything else?"), but never give answers.
   - At 5 minutes it is "let's move on", even if questions are left.
   - In exam mode there is no feedback during the viva, as in the real exam.
   - Debrief: the mark of each topic with one line on why. For every miss, the model answer, then a retry. Cards you
     keep failing are taught.
   - Then type `REPORT` and copy the JSON.
4. **Mark.**
   - Paste the report here. Claude Code runs `python3 tools/examiner.py mark <sid> report.json`, which:
     - prints each topic's mark (with a cross-check mark computed from the answers);
     - prints the viva result (pass when the total reaches 6 per topic);
     - updates every card's schedule;
     - then commits `examiner/`.
   - If there is no report, paste the transcript. Claude grades it against `examiner.py show <sid>`.

`python3 tools/examiner.py status` shows:
- what is due;
- the tiers and the must-know cards not started yet, per chapter;
- your average topic mark per viva;
- your recent viva results;
- your weakest cards.

## The viva format

| | As in the board viva | Here |
|---|---|---|
| Topics | 5 minutes each, three per examiner | `TOPIC_MIN` 5, up to 5 short questions, two examiners |
| A full viva | 30 minutes, 6 topics | `session` (default 6 topics) |
| Four vivas | themed to cover the curriculum | critical care / basic science (Ch 1–6), adult cardiac (Ch 7–11), congenital (Ch 12), thoracic (Ch 13–17) |
| Topic sheet | a topic asked once is not asked again that day | topics examined today are left out of the next plan |
| Marks | 4 bad fail, 5 fail, 6 pass, 7 good pass, 8 very good pass | the same, with the descriptors in `MARKS` |
| Result | marking episodes add up | pass when the total reaches 6 × the topics; bad fails are flagged |
| Feedback | none during the exam | exam mode: none until the debrief (`--mode practice` gives it after each answer) |

Sources and limits:
- The 5-minute topics, the 4–8 scale and the topic sheet follow the published account of the Intercollegiate
  Section 2 viva for Trauma & Orthopaedics; the Intercollegiate specialty exams share that framework.
- The grouping of the book's chapters into four vivas is ours.
- The JCIE's own regulations are the authority on the cardiothoracic exam's details.
- The book is the *Oxford Specialist Handbook in Cardiothoracic Surgery*; the board exam itself is the Intercollegiate FRCS.

**Topic marks**

| Mark | Meaning |
|---|---|
| 8 very good pass | complete, structured and fluent, safe throughout, reaches the top of the ladder with little or no prompting |
| 7 good pass | safe and well organised, minor gaps only, few prompts |
| 6 pass | safe, gives the essentials, needs some prompting, does not get far up the ladder |
| 5 fail | gaps in the essentials or needs leading, but nothing dangerous |
| 4 bad fail | a dangerous answer, or cannot give the essentials even with prompting |

`mark` also computes each topic's mark from the answers, weighted by importance:
- a confident wrong answer on a must-know card gives 4;
- 8 needs a topic climbed to the management rung or higher.

This computed mark is a cross-check, and it is the topic's mark when the examiner gives none.

## Importance: what to meet first

Every card is rated when it is written, on five criteria, each scored 0–3. They are judged for a cardiothoracic
surgeon and a board examiner, against the whole specialty, not the page. This is how certifying boards weigh exam
content: in their practice analysis and exam blueprints, how critical and how frequent a task is decide how much it
counts. We add two more criteria: how much management turns on the fact, and how much else is built on it.

| Criterion | Weight | 0 | 3 |
|---|---|---|---|
| safety: harm if you don't know it | 30% | none | death or catastrophe (emergency, red flag, absolute contraindication) |
| decision: does it change what you do | 25% | background, history | decides whether or what to operate (indication, threshold) |
| frequency: how often you meet it | 20% | a rarity | every day, every patient |
| exam: how often examiners ask it | 15% | never | a classic (classification, guideline indications, scores, numbers) |
| core: how much else depends on it | 10% | stands alone | a foundation (anatomy, physiology) |

The tool computes the score (0–100) from these ratings; the writer never picks it. The tier follows from the score:
- **A, must know:** a score of 65 or more. Anything rated safety 3 is also tier A whatever its other ratings, because
  a fact that can kill is a critical item.
- **B, should know:** a score of 40 or more.
- **C, nice to know:** the rest.

Importance is used in four places:
1. **Topic order.** A topic's urgency is the sum of its most urgent cards. A due card scores
   1 + forgetting × importance, and a confident error adds 1. A new card scores its importance.
2. **Climbing order.** Within a topic, the most important cards are chosen first, then asked up the ladder.
3. **Retention.** The FSRS target retention is 95% for A, 90% for B and 85% for C, so A cards come back sooner.
   Examiners are strictest on A cards.
4. **Tier C is never dropped.** Its cards simply come later.

Ratings can creep up when a writer rates page by page. `add` and `rank` warn when more than 40% of cards are tier A
(across the book it should be about a quarter) or when a large set has no tier C at all. Some chapters, trauma for
example, can honestly run high. `rank --chapters 1` lists the cards by score with each one's reason, so you can check
the ratings by eye.

## How each answer is rated

| What the examiner saw | Rating |
|---|---|
| wrong, blank, under half the key points, or right only after 2 prompts | Again |
| partial (half or more of the points), right after 1 prompt, or a correct guess | Hard |
| right but hesitant, unsure, or not every point | Good |
| every key point, at once, no prompt, sure | Easy |

- **Once failed, never Easy.** A card you have failed before gets at most Good.
- **Debrief retries are capped at Good.** They count as a same-day review: short-term memory, not learning.
- **A failed card brings its siblings forward.** The cards on the same page and its `related` cards move to tomorrow.
- **Leeches are taught.** After 4 failures a card is taught in the debrief instead of being drilled.
- **The examiner reads your last note.** Each card keeps its last notes ("mixed up class III and IV"), and the next
  examiner tests exactly that.

FSRS-6 here is py-fsrs 6.3.2 (`pip install fsrs==6.3.2`), the same engine the app's `Fsrs.kt` is verified against.
It runs without learning steps, because a viva is a day-scale event.

## Files (all text, committed)

**`examiner/bank/chNN.json`** holds one chapter's page facts and cards:
```json
{"chapter": 1, "title": "...",
 "pages": {"2": {"facts": ["...", "..."]}, "11": {"skip": "full-page figure"}},
 "cards": [...]}
```
A card looks like this:
```json
{"id": "ch01.p002.01", "chapter": 1, "page": 2, "topic": "Cardiovascular history",
 "type": "recall|list|why|case|compare|value", "level": 1,
 "q": "...", "a": "...", "points": ["..."], "facts": ["p002.f01"],
 "importance": {"safety": 0, "decision": 0, "frequency": 0, "exam": 0, "core": 0, "why": "..."},
 "related": ["..."]}
```
- `level` runs from 1 to 4 and each importance criterion from 0 to 3.
- A question is at most 160 characters and an answer at most 300.
- `page` is the printed book page.

**`examiner/state.json`** holds, for every card: the FSRS card, reps, lapses, history (every rating with its
reason), notes and the leech flag. It also lists the marked sessions and every viva with its topic marks and result.

**`examiner/sessions/<sid>.plan.json` and `<sid>.report.json`** record what was asked and what happened.

**`work/examiner/`** holds the page text and the examiner prompts. It is ignored by git, because it can be rebuilt.
