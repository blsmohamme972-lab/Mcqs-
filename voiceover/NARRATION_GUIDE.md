# Writing the spoken lines

`voiceover.py make` (or `draft`) creates `voice/<QID>.voice.json` with one entry per beat (the card's numbered captions). Each `say` line is **pre-filled with the caption**. Edit only the lines `make` lists as too long, or ones that read badly aloud.

**Least effort (Golden rule 8):** write the captions themselves short and speakable when authoring the card: within the word budget (about 6 / 5 / 6 words on an 8 s card), no arrows or symbols. The voice then needs no edits.

## Rules

1. **One short spoken line per beat.** Stay within the word budget `draft` prints. On an 8 s card that is about 6 / 5 / 6 words. The voice talks at about 2.6 words per second.
2. **Say what the animation shows at that moment**, in the same order. The line starts with its caption and its animation step (Golden rule 7).
3. **Spoken English, not caption text:**
   - no arrows, symbols or abbreviations the ear can't parse
   - write "ammonia", not "NH₃"; `lexicon.json` expands the common ones (INR, PO₂, →)
4. **Never contradict the source answer or explanation.** Never say option letters ("C is correct") and never add facts the card doesn't show. The host shows the correct answer after the card.
5. **Plain and calm.** Short sentences, present tense, no filler ("so basically…"). A colon gives a natural pause: "Ketones build up: acidosis."
6. **The last beat carries the takeaway.** It may run up to the final hold (350 ms before the end).
7. If `synth` says a line doesn't fit, **cut words**. Don't lengthen the card, unless the owner set a longer duration.

## Fields

```json
{"qid": "Q000009379", "duration_ms": 8000, "voice": "af_heart", "lang": "en-us", "speed": 1.05,
 "beats": [{"start_ms": 0, "end_ms": 2700, "caption": "No insulin: glucose cannot enter the cells", "say": "No insulin: glucose can't enter."}, …]}
```

- `voice`: `af_heart` (default, best rated) or `bf_emma` with `"lang": "en-gb"` for a British voice. Use one voice per book.
- `speed`: 1.05 by default. `synth` raises it up to 1.2 when a line runs long. A beat can set its own `speed`.

## Scenes without numbered captions

A script-drawn card often has no `1 · …` caption layers:
- **If its script declares captions as `caps(api, P, [[start_ms, end_ms, "text", colour], …])`**, `draft` reads the beats from it. An `end_ms` of 0 means "to the end of the card".
- **If not, `draft` writes even, guessed beats**, each marked `"timing": "guess"`, and `synth` refuses the card until you fix them:
  1. Set each beat's `start_ms` and `end_ms` to when that step of the animation starts and ends (read the scene's `script`).
  2. Write its `say` line.
  3. Delete `"timing": "guess"`.
  4. Run `make` again.

## After `synth`

`make` (or `check`) must say **CHECK PASS**:
- **A word that "sounds like" something else:**
  1. Add the word to `lexicon.json`: `say` for an abbreviation or symbol, `ipa` for a word the voice mispronounces (copy the pattern of the existing entries).
  2. Run `make` again.
  3. If the word still fails, reword the line.
- **"Heard more" or "sound outside the spoken lines":** run `synth` again. If it repeats, listen to the review video.
- **Listen:** watch at least one `review` MP4 per batch with sound.
