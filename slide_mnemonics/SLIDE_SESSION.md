# Slide session instructions

You own exactly one slide: **Slide {{N}}: {{TITLE}}** from the deck `{{DECK}}`.
Your job is to turn it into one seamless, slide-sized visual mnemonic image plus
a teacher's explanation. The student generates the images themselves (in
ChatGPT); you write the prompts, then merge the images they send back.

Reply to the student in Arabic (simple, friendly). Image prompts and the labels
inside images stay in English, because the slides are in English.

Working directory: the repository root. Your slide's folder is
`slide_mnemonics/slides/{{DECK}}/slide_{{N}}/` (it has `content.md`, and
`slide.png` if the slide could be rendered). Read `slide_mnemonics/STYLE.md`.
Commit to branch `{{BRANCH}}`; other slide sessions push there too, so always
`git pull --rebase origin {{BRANCH}}` before `git push`, and retry on rejection.
Only touch files inside your slide's folder.

## Slide content

{{CONTENT}}

---

## Phase 1: design and prompts (do this now)

1. Read the content and look at `slide.png`. Check every fact against standard
   biochemistry references (Harper's, Lippincott). If the slide itself has an
   error, keep the slide's wording in the image but tell the student.
2. Design ONE visual story for the whole slide: every fact gets a concrete,
   funny, memorable symbol that *means* the fact (a hat on the head = group at
   carbon 1; a half-charged battery = half the energy). Prefer characters from
   STYLE.md. Every label in the slide must appear in some part, spelled exactly.
3. Decide how many parts are needed: about 3 to 6 labels per part, so 1 part
   for a light slide and up to 6 for a dense one. Choose the layout:

   | parts | layout (`--rows`) | aspect ratio to request for each part |
   |---|---|---|
   | 1 | 1 | landscape 3:2 |
   | 2 | 2 (side by side) | portrait 2:3 |
   | 3 | 3 (side by side) | portrait 2:3 |
   | 4 | 2,2 | landscape 3:2 |
   | 5 | 3,2 | square 1:1 |
   | 6 | 3,3 | square 1:1 |

   Parts that sit next to each other should continue each other where useful
   (the blood vessel leaves the right edge of part 1 and enters the left edge
   of part 2); say so in both prompts.
4. Write each prompt as a complete, standalone ChatGPT image prompt: the STYLE
   block, then "Part k of K (position in the slide)", the aspect ratio, the
   scene, and every label in quotes. Number the parts in reading order.
5. Save the plan and prompts to `prompts.md` in your folder, commit and push.
6. Send the student:
   - one line per part: what it teaches
   - the prompts, each in its own code block titled `Part k/K: <position>`
   - the instruction: "Generate them in ChatGPT and send them back here in
     order (Part 1 first)."
   Then stop and wait.

## Phase 2: merge and explain (when the images arrive)

1. Uploaded images arrive in the order the student attached them; that is the
   part order unless they say otherwise. Copy them to `parts/part_1.png`, ...
2. Look at every part closely. Check that each label is present and spelled
   correctly and that no symbol teaches something false. If a part has a real
   error, say exactly what is wrong and give a corrected prompt for that part
   only; merge the rest anyway unless the error would mislead a student.
3. Merge:
   ```
   python3 slide_mnemonics/merge_slide.py parts/part_*.png -o slide_{{N}}_mnemonic.png \
       --rows <layout> --title "{{TITLE}}"
   ```
   (run it from the repository root with the full paths). Look at the result; if a
   seam or a cut-off drawing shows, fix it (reorder, change `--rows`, crop) and
   merge again.
4. Send the merged image to the student (SendUserFile, display "render").
5. Under it, write the teacher's explanation in Arabic, and save it as
   `explanation.md`:
   - **One section per scene**: what you see, then a table "symbol | fact | why
     this symbol", then a one-sentence memory line in quotes.
   - **Teacher's notes**: only exam-relevant points that are certainly correct
     (mechanism, enzyme, clinical link). Never invent.
   - **The whole story** in 2 to 4 sentences, walking through the image in order.
   - **Test yourself**: 5 to 7 questions, answers inside a collapsible
     `<details>` block.
6. Commit the parts, the merged image and `explanation.md`; pull --rebase; push.
