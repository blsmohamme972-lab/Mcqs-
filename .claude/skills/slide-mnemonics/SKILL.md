---
name: slide-mnemonics
description: Turn a PowerPoint deck into visual-mnemonic images, one Claude Code session per slide. Use when the user uploads a .pptx (or names one) and wants mnemonic images, image prompts, or a teacher's explanation per slide.
---

# Slide mnemonics: main agent

You are the main agent. You do not design images yourself. You split the deck
and open one session per slide; each slide session writes the image prompts,
merges the images the student sends back into one 16:9 slide image, and writes a
teacher's explanation (see `slide_mnemonics/SLIDE_SESSION.md`).

Talk to the student in Arabic.

## Steps

1. **Find the deck.** The .pptx is either an uploaded file (look in the
   uploads directory named in the conversation) or a path the student gives.
   Pick a short deck name, e.g. `carbohydrates-ch1`.

2. **Extract the slides.**
   ```
   python3 slide_mnemonics/extract_slides.py <deck.pptx> --out slide_mnemonics/slides/<deck>
   ```
   Read `slides.json`. Show the student a numbered list: slide number and
   title, marking slides with no teaching content (title page, "Thank you",
   references, empty) as "skip".

3. **Confirm before opening sessions.** Each session costs usage, so ask
   (AskUserQuestion): all teaching slides, or a range. Default to the teaching
   slides only. Do not open sessions without this answer.

4. **Publish the slide files.** Commit `slide_mnemonics/slides/<deck>/` and
   push to the current branch. The slide sessions start from that branch, so
   they must see the files.

5. **Build each session's first message.**
   ```
   python3 slide_mnemonics/build_session_prompts.py slide_mnemonics/slides/<deck> \
       --branch <current-branch> --slides <chosen list>
   ```
   Commit and push the generated `session_prompt.md` files too.

6. **Open one session per chosen slide** with `create_session`
   (claude-code-remote tools; load them with ToolSearch if needed):
   - `title`: `Slide NN · <slide title>` (two-digit number, so sessions sort)
   - `prompt`: the full contents of that slide's `session_prompt.md`
   - `source_url`: this repository's GitHub URL
   - `source_revision`: the current branch
   - `tags`: `["slide-mnemonics:<deck>"]`
   Open them in batches of up to 5 at a time, and check each result. If one
   fails, retry it once, then report it.

7. **Report back** in a table: slide number, title, session title, session
   link or ID. Tell the student:
   - open each session in the Claude app; its prompts are waiting there;
   - generate the images in ChatGPT and send them **back to the same session**,
     in order;
   - that session will send the finished slide image and the explanation.

## Later

- "Status?": use `list_sessions` with the deck tag and `get_session` to say
  which slides are waiting for images and which are finished (a finished slide
  has `slide_NN_mnemonic.png` in its folder after a `git pull`).
- "Redo slide N": open a new session for that slide the same way.
- Never mix slides: one session = one slide = one merged image.
