# Instructions for ChatGPT: Kafu image queue

You make one teaching illustration per MCQ and save it to Google Drive. Claude turns each
image into a narrated image lesson for the Kafu app. You do NOT need to edit anything on GitHub.

## Where things are

- Queue pages (read only): `kafu_queue/queue/<PACKAGE>.md` in https://github.com/blsmohamme972-lab/Mcqs-
  on branch `claude/ai-biochemistry-image-generation-efl9y3`. Each page lists up to 10 questions.
  Under each `## <QID>` heading there is a ready prompt in a code block.
- Save images to the Google Drive folder "Books":
  https://drive.google.com/drive/folders/1A2_GAFmrM-EugAztWI6FgqbAuvXZWNSU

## For each question in the package, in order

1. Generate the image from its prompt, exactly as written. Landscape 3:2 (1536x1024).
2. Check it before saving:
   - every label in the prompt is present and spelled exactly;
   - the bottom banner starts with `Answer -->` and shows the answer from the prompt;
   - nothing gory, no real photos, no watermarks.
   If a label is wrong or missing, regenerate once.
3. Save it to the Drive folder with the file name **exactly `<QID>.png`**, e.g. `Q000000033.png`
   (capital Q, the digits from the heading, `.png`). No other name, no extra words.
   This name is the only way Claude knows which question the image belongs to.
4. Go to the next question. When the package is finished, reply with one line:
   `<PACKAGE>: saved N/N` and the QIDs of any you could not save.

## Rules

- Do not change the answer or add facts that are not in the prompt.
- Do not save drafts or duplicates to the folder. If you must replace an image, overwrite the same file name.
- If you cannot save to Drive, say so plainly and give the download links instead; do not claim it was saved.
