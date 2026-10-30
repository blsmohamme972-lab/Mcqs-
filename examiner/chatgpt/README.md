# ChatGPT saves the viva itself: the "Viva examiner" GPT

ChatGPT's normal GitHub connection can only read the repository, so its saves fail with 403. This setup gives a GPT
of your own exactly one write door into the repository: it sends the viva REPORT, and the repository does the
rest by itself:

```
"Viva examiner" GPT ──saveVivaReport──> GitHub (repository_dispatch "viva-report")
                                             │
                    .github/workflows/viva-report.yml: tools/examiner.py inbox
                    (FSRS for every answer, viva marks, next viva, VIVA.md) ──commit──> examiner/
```

The GPT never computes anything, never edits files, and never needs Claude Code. If a report cannot be marked, the
workflow keeps it in `examiner/inbox/`, so Claude Code can repair it by hand and nothing is lost.

بالعربي: تسوي GPT خاص بيك مرة وحدة. هو يقرا الفايفا من الريبو، يمتحنك بالصوت، ويحفظ النتيجة بنفسه. الريبو يحسب
المراجعات ويكتب الفايفا الجاية. تحتاج اشتراك ChatGPT مدفوع (حتى تسوي GPT) وتوكن من GitHub.

## One-time setup (about 10 minutes)

**1. A GitHub token that can write only to this repository**

1. On GitHub go to **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new
   token**.
2. Fill in the token:
   - Name: `Viva GPT`.
   - Expiration: whatever you like (for example 1 year).
   - Repository access: **Only select repositories → Mcqs-**.
   - Permissions → Repository permissions → **Contents: Read and write**. Nothing else.
3. Click **Generate token** and copy it. GitHub shows it only once.

**2. The GPT**

1. In ChatGPT go to **GPTs → Create → Configure**.
2. Fill in the basics:
   - Name: `Viva examiner`.
   - Instructions: paste the whole of [`instructions.md`](instructions.md).
   - Capabilities: leave **Web search** on, for the fallback link.
3. Add the action. Go to **Actions → Create new action**:
   - **Authentication:** API Key, Auth Type **Bearer**, and paste the token.
   - **Schema:** paste the whole of [`openapi.json`](openapi.json). It should list two actions, `getVivaPage` and
     `saveVivaReport`.
4. Save the GPT as **Only me**. The GPT holds a write token, so never share it.

**3. One file on `master` (done once by Claude Code with your permission)**

GitHub starts `repository_dispatch` workflows only from the default branch. So
`.github/workflows/viva-report.yml` has to be on `master` as well. It works on the branch that holds `examiner/`,
`EXAMINER_BRANCH` in the file.

## Every day

1. Open the **Viva examiner** GPT, start voice and say "start".
2. Sit the viva.
3. After the debrief it shows the REPORT and saves it by itself.
4. A minute later say "check": it reads the page back and tells you your marks and the next viva.

## If something goes wrong

- **401 or 403 from saveVivaReport:** the token has expired or lacks *Contents: Read and write* on Mcqs-. Make a new one
  and paste it into the action's authentication.
- **404 from saveVivaReport:** the token cannot see the repository. Check its repository access.
- **Saved, but the page doesn't change after a few minutes:** look at Actions → "Save viva report" on GitHub, or paste
  the REPORT to Claude Code. A report the workflow could not mark is kept in `examiner/inbox/`.
