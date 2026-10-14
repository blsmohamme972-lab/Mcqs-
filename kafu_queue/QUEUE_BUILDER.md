# Building a queue from a chapter export (Claude)

The owner sends a chapter export (`kafu_mcq_text_export` JSON from the app). Turn it into packages
whose image prompts ChatGPT will draw.

1. Split (4 questions per package, `batch_size` in config.json; small packages build in parallel; the package id becomes the lesson PACKAGE ID):

       python3 kafu_queue/make_queue.py split <export.json> --pkg-prefix <BOOK>-CH<N> [--qids ...] [--already-live]

   Use short ids like `BAILEY-CH1` or `GT-CH2`. Skip questions the owner names. `--already-live` when
   these questions already have an animation in the app.
2. Fill `"prompt"` for every item in `kafu_queue/queue/<PKG>.json`, then `make_queue.py render <PKG>`.
3. `make_queue.py check` must say OK for every package. Commit `kafu_queue/` (queue + exports) and push.
4. Tell the owner, in one short Arabic message, which packages are ready for ChatGPT and that ChatGPT
   should follow `kafu_queue/GPT.md`.

## How to write each image prompt

Facts only from the stem, the answer and the explanation; never change the key, never invent numbers.
If the explanation is wrong or does not explain the key, draw the short, standard, correct reason that
supports the key (and note the QID in the commit message).

Template (keep this structure; about 900-2500 characters):

```
Create a landscape 3:2 image (1536x1024). Picmonic-style visual mnemonic, fun and medically accurate, for
medical students: cute cartoon characters with big friendly eyes, bright flat colors, thick dark outlines,
clean pale background, each fact drawn as a memorable visual pun. All text sits in rounded white label
boxes with dark navy bold letters, crisp and spelled exactly as given.
Title banner at the top: "<topic in 2-5 words>".
<3-5 scenes, left to right, each: what is drawn + why it means the fact + its label(s) in quotes>
Bottom banner: "Answer --> <the answer in at most 8 words>".
Avoid: garbled or misspelled text, duplicated characters, distorted faces, realistic gore, photographs,
watermarks, cluttered dark background.
```

Lessons from testing (ChatGPT and Qwen, 2026-10-14):
- 6 to 12 labels in total, 1 to 4 words each. Long lists in one label (e.g. "CN III IV V1 V2 VI") come out
  garbled: give each item its own short label, or draw it with colors and no text.
- One story that flows left to right. Every arrow or path must actually reach where the story says (a vein
  must visibly enter the sinus it drains into).
- Keep the main character small enough (about a third of the width) to leave room for the other scenes.
- Do not reuse the same object for two meanings (yellow grapes = bacteria, so the clot is not grapes).
- The bottom banner must start with `Answer -->`: the lesson builder checks it against the key.
- Questions with book images (`has_book_images: true`): describe only what the stem and explanation say.

## Running a big batch (e.g. 100 questions)

1. `split` makes about 25 packages of 4. Write the prompts, `render` each, `make_queue.py check`, commit and push.
2. ChatGPT: `python3 kafu_queue/watch.py gpt-prompts` prints one ready prompt per chat (5 images each, 20 chats for 100
   questions) with the right queue pages and only the QIDs still missing. Re-run it any time: it lists what is still missing.
3. Builders start by themselves as packages complete (WATCHER.md, at most `max_concurrent_builders` at once); to start one by hand:
   `python3 kafu_queue/watch.py builder-prompt <PKG>` prints the full prompt for `create_session` (never message an old session).
4. Upload to the bot: each package is its own ZIP and publishes on its own, nothing to merge. Send them 5 at a time, about
   2 minutes apart; wait for the "published" replies; `/motioncards-status` shows anything stuck; a package "running" for more than
   10 minutes usually means its GitHub Actions run (Publish Kafu MotionCards Queue) failed at "Verify MotionCards production after
   promotion": open the run and press "Re-run failed jobs", then check `/motioncards-status` again.
