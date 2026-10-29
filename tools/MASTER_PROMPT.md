# MCQ BOOK PACKAGER — MASTER PROMPT (schema 1)

I attached: (1) a medical MCQ book (PDF), (2) `validate.py`, and (3) `audit.py`.
Your job: turn this book into ONE publish-ready ZIP package (split only when the measured limits in Section 7 require it), working entirely with code in your sandbox. Do the whole job yourself. Only stop to ask me if the book cannot be processed at all.

Optional settings (blank = you decide):
- SPECIALTY:
- FIELD: medicine
- COLLECTION_TYPE: textbook   (use past_exam for previous-years questions)
- BOOK_ID:

---

## 0. Golden rules (never break these)

1. **Copy, never write.** Every question, option and explanation must come from the PDF text through code (PyMuPDF / pdfplumber / pypdf — whichever is installed). Never retype from memory, summarise, paraphrase, translate or "improve" wording.
2. **Never correct the medicine.** If a book answer looks wrong, keep the book's answer and write your concern in `flag`.
3. **Never guess an answer.** Answers come only from the book's answer key or an answer marked in the text. If you cannot find a question's answer, leave that question out and list it in `skipped` with the reason.
4. **Never drop a question silently.** Every number in the book appears in `questions.jsonl` or in `skipped`.
5. **Do not edit `validate.py` or `audit.py`.** After extraction, run `python audit.py SOURCE.pdf PACKAGE.zip --output audit.json`, place `audit.json` in the ZIP, then run `python validate.py --require-audit <zip>`. The package is finished only when the validator prints `RESULT: PASS`.

## 1. Map the book first

Before extracting, open the PDF with code and write a short book map in your reply:
- text PDF or scanned (no text layer)?
- where questions are, and where answers/explanations are (after each question, end of chapter, or end of book)
- numbering scheme (continuous 1…N, or restarting each chapter)
- question formats present: SBA (single best answer), MTF (multiple true/false), multi-select ("choose two"), EMQ (extended matching)
- chapters, total question count stated by the book (if any), pages with figures

## 2. Extract with a parser, not by hand

Write a parser for THIS book's layout and run it over the whole PDF. The parser is part of the deliverable, not disposable scratch code.

Parser delivery rules:
- Save it as a standalone Python module named for the layout/book, compatible with the contract in `tools/parsers/README.md`.
- It must export `parse_pdf(pdf_path)` and deterministically return `questions`, `chapters`, `skipped`, and optional `notes`.
- Do not hide extraction logic in notebook state or one-off shell commands.
- Include layout assumptions in the parser docstring so a helper can rebuild the same book later without an AI chat.
- If the PDF is scanned or requires visual/OCR work that cannot be deterministic, say so explicitly; do not pretend the parser can reproduce it.

Then run it over the whole PDF. Clean the text:
- remove running headers, footers, page numbers, publisher lines
- replace ligatures (ﬁ ﬂ ﬀ ﬃ ﬄ) with normal letters
- **HYPHENS:** For a word split with a hyphen at a line end (e.g. "fol-" followed by "lowing"), join it with no space and remove the hyphen only if the same word appears elsewhere in the book without it ("following"). Keep real hyphens like "two-thirds". If the unhyphenated word cannot be confirmed elsewhere in the book, join with no space, keep the printed hyphen, and do not flag it.
- keep symbols and units exactly; use Unicode (PaO₂, Na⁺, µg, ≥, ±), never LaTeX
- keep tables as simple Markdown tables; remove PDF line breaks inside a paragraph; keep only real paragraph breaks, lists, and tables
- strip option labels from option text ("A. Ketamine" → "Ketamine")

**Scanned PDF:** read pages visually in batches of about 20 pages, transcribe exactly, and append each batch to the JSONL file with code before moving on. If the book is too long for one session, save the working files and the exact resume page; processing batches are not delivery ZIP parts. Apply Section 7 to the complete book before choosing one ZIP or parts.

## 3. Numbering and answers

- `local_id`: 1, 2, 3 … in book order across the whole book (never restart, never reuse).
- `source_number`: the number exactly as printed ("12", "3.12", "Q12").
- Match answers to questions by chapter + printed number, then check: every answer letter exists among that question's options; the number of answers equals the number of questions in each chapter.
- `answer_source`: `"book_key"` (answer key / explanation section) or `"inline_marked"` (answer shown next to the question).

## 4. Question formats

| type | options | answer |
|---|---|---|
| `sba` | 3–8 | one letter: `"C"` |
| `mtf` | 2–10 statements | list of T/F, one per statement: `["T","F","T","T","F"]` |
| `multi` | 3–12 | list of 2+ letters: `["A","D"]` |
| `emq` | 5–26 (the theme's shared list) | one letter; split each item of the theme into its own question with the same `group_id` (e.g. `"EMQ-7"`), the theme's instruction in `lead_in`, the item scenario in `stem` |

If any option depends on position ("All of the above", "None of the above", "Both A and C", "Only B") set `"no_shuffle": true`.

## 5. Images

- **FIGURES:** Attach an image to a question only if the question cites its figure number (e.g. "Fig. 29-4") and that number matches the figure’s caption in the book. Never attach an image just because it is on the same page. If unsure, attach nothing and flag it. This matching rule also applies to explanation images: require the explanation’s cited figure number to match the caption. Skip logos, icons, decorative chapter art.
- Crop to the figure only. Convert to WebP: max width 1200 px, quality 80, under 1.5 MB.
- Name by `local_id`: question images `L0041_1.webp`, `L0041_2.webp`; explanation images `L0041_e1.webp`. Put them in `images/`.
- Cover: the book's front cover (or page 1) as `cover.webp`, about 600 px wide, under 400 KB.

## 6. Files inside the ZIP (top level, nothing else)

```
book.json
questions.jsonl
cover.webp          (part 1 only)
images/             (only if the book has figures)
audit.json          (source-consistency audit; required)\nreport.md           (your short summary)
```

**book.json**
```json
{
  "schema": 1,
  "book_id": "ANES-REVIEW-1000-1E",
  "title": "Anesthesia Review: 1000 Questions and Answers",
  "subtitle": "",
  "authors": ["First Author", "Second Author"],
  "edition": "1st",
  "year": 2014,
  "publisher": "",
  "field": "medicine",
  "specialty": "Anesthesiology",
  "branch": "",
  "collection_type": "textbook",
  "language": "en",
  "version": 1,
  "expected_count": 1000,
  "part": {"index": 1, "total": 1},
  "id_range": [1, 1000],
  "chapters": [{"id": 1, "title": "Pharmacology"}, {"id": 2, "title": "Physiology"}],
  "skipped": [{"local_id": 417, "reason": "answer missing from the key"}],
  "license_note": ""
}
```
- `book_id`: UPPERCASE letters, digits and hyphens (short title + edition). Keep it identical in every part.
- `specialty`: exactly one name from `ALLOWED_SPECIALTIES` in `validate.py`.
- `expected_count`: total questions the book contains (or `null` if unknown).
- `id_range`: first and last `local_id` in THIS part. Every id in the range is in `questions.jsonl` or `skipped`.

**questions.jsonl** — one JSON object per line, in book order:
```json
{"local_id": 41, "chapter_id": 3, "topic": "Diuretics", "type": "sba", "source_number": "41", "lead_in": "", "stem": "…", "options": ["…", "…", "…", "…", "…"], "answer": "C", "answer_source": "book_key", "explanation": "…", "images": ["L0041_1.webp"], "explanation_images": [], "group_id": "", "no_shuffle": false, "source_page": 112, "flag": ""}
```
- `explanation`: `""` if the book has none. `topic`: `""` if unclear.
- explanation: 2–4 complete sentences copied from the book's explanation. If shorter, copy it whole. Do not flag short explanations.
- source_label: "Book Name || Edition" on every question.
- `source_page`: the PDF page where the question starts.
- `flag`: `""`, or a short reason if anything is uncertain (unclear scan, doubtful answer, figure not found).

## 7. Size and parts

**Size preflight, step 1 (limit discovery):** Read the current bot import code and `validate.py` without editing them. Record every real size/count limit with its file and line in `report.md`; do not invent a smaller ZIP, question-count, image-count or JSON budget. The currently enforced incoming-package limits are:

| Limit | Actual code rule | Source |
|---|---|---|
| Compressed ZIP | At most 19,922,944 bytes (19 * 1024 * 1024 = 19 MiB); deliver strictly below this ceiling. | `worker/queue-state.mjs:2,21`; `tools/drain_queue.py:32,89`; `tools/validate.py:46,434-436`; `migrations/0001_publish_queue.sql:24` |
| Uncompressed ZIP contents | At most 209,715,200 bytes (200 MiB) of counted file contents. | `tools/validate.py:47,371,376-377` |
| ZIP entries | At most 5,000 entries, including directory and junk entries. | `tools/validate.py:48,340-343` |
| Compression ratio | At most 100:1 for each member with a nonzero compressed size, not an archive-wide ratio. | `tools/validate.py:49,372-374` |
| Each question/explanation image | At most 1,500,000 bytes and 1600 px wide; keep the Section 5 target of 1200 px. | `tools/validate.py:50,52-53,487-494` |
| Images per question | At most 6 in `images` and separately 6 in `explanation_images`; no separate whole-pack image-count ceiling beyond the entry/byte limits. | `tools/validate.py:311-317,340-343` |
| Cover | At most 400,000 bytes; required in part 1. | `tools/validate.py:51,465-473` |
| Parts and filename | At most 100 parts per release; filename at most 255 characters. | `worker/queue-state.mjs:6,10`; `migrations/0001_publish_queue.sql:5` |
| Questions and JSON per incoming pack | No independent question-count or JSON/JSONL byte ceiling; the archive byte, entry and ratio limits still apply. | `tools/validate.py:390-404,448-449,497-530`; `tools/validate_release.py:21-45`; `tools/publish.py:51-112` |

The "19 MB" wording in DELIVER means the code's 19 MiB budget above, not permission to upload 20 MB. Use exact byte measurements, not rounded file-card sizes or estimates. The code accepts equality at 19,922,944 bytes; this prompt deliberately requests a file below that boundary. Image/cover byte limits use decimal bytes, as shown.

**Size preflight, step 2 (measurement):** Build and measure the complete final single ZIP first, including all questions, figures, table crops, cover, `book.json`, `audit.json` and `report.md`. Record its exact compressed bytes, counted uncompressed bytes, entry count and maximum member ratio. Recheck the actual final archive after every content, compression, audit or report change. An earlier estimate or intermediate archive is not a reason to retain a split when the final single ZIP fits.

**SIZE:** Deliver ONE ZIP if it is under 19 MB. Split into parts only if it is bigger. Use the exact byte budget defined above; do not split an otherwise small ZIP because of chapter, question or image counts.

**Size preflight, step 3 (split only if required):** If the complete final ZIP is below the compressed-size ceiling, deliver that ONE ZIP after it passes all other applicable limits. Split only when its compressed size exceeds that ceiling, making each part as large as allowed and using the fewest parts. If a ZIP is exactly at the ceiling, reduce its compressed size below the boundary before delivery. An under-ceiling ZIP that fails another limit must be repaired or reported as blocked, not split merely for that reason. Prefer chapter boundaries only when they do not cause extra parts; a chapter may span parts while keeping its chapter ID and full-book local IDs. Do not split merely because the book has many chapters/questions/images, because it was processed in batches, or to target an arbitrary smaller ZIP size. Each part must pass every limit and the unchanged validator. Name parts `BOOK-ID_v1_part1ofN.zip`, etc.; keep the same `book_id`, version and chapter definitions, each part's own `part` and contiguous `id_range`, only its own questions/images/skipped entries, and `cover.webp` in part 1. Rebuild the audit for each final `questions.jsonl` and run `validate_release.py` on the complete release.

For any split, `report.md` must name the specific violated limit and its source line, the measured attempted single-ZIP value versus the allowed value, the exact size/entry/expanded-byte values for every part, and why fewer parts cannot fit. Splitting cannot repair an oversized individual image, excess images attached to one question, invalid source content, or another per-item validation error; resolve the actual issue without dropping source material or weakening validation.

Downstream limits are not smaller incoming-pack budgets: `tools/http_client.py:14,77-95,116-125` caps each default HTTP response at 64 MiB, and `tools/publish.py:175-180` stops global permanent-ID allocation above 999,999,999. The publisher reassembles input parts and builds chapter assets; splitting an upload cannot bypass a downstream chapter-response limit or global ID exhaustion. Report such a blocker separately instead of manufacturing more ZIP parts.

## 8. Self-check before delivering

1. Run `audit.py` against the current parser output. **Every audit mismatch must be fixed in the parser/output before delivery; never ship a mismatch.** Re-run the parser and audit until mismatch count is zero.
2. For audit warnings, investigate each one and improve the parser/source-page mapping where deterministic source evidence allows it. Re-run `audit.py` after each parser fix until warnings are as low as reasonably possible without changing, guessing, or medically correcting source content.
3. Record every remaining audit warning in `report.md` with local ID/source number, page, and audit reason. A remaining warning does not change the book answer and does not require owner approval.
4. Run `python validate.py --require-audit <each zip>`. Fix every ERROR and re-run until `RESULT: PASS`. `validate.py` is unchanged and is the same gate used by the server.
5. Spot-check 15 random questions: print the source page text next to your extracted JSON and confirm stem, options and answer match exactly. Fix any mismatch and re-run the audit and validator.
6. Confirm the counts: questions + skipped = `expected_count` (when known).

## 9. Deliver

Give me only:
- **SIZE:** Deliver ONE ZIP (BOOK-ID_v1.zip) if it is under 19 MB. Split into parts only if it is bigger, making each part as large as allowed (fewest parts). Every delivered ZIP must still pass the bot’s other real limits and the unchanged validator. State in the report why a split was needed.
- the parser source file you used, ready to save under `tools/parsers/`
- a short parser note: layout assumptions and the exact `tools/package_batch.py` command that can rebuild the package
- a 5-line summary: title, questions per type, skipped (with reasons), flagged count, images count, and the final `RESULT: PASS` line.

The work is not complete if the ZIP passes but the parser that produced it is missing.