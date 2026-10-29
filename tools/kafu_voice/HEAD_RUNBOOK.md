# Kafu Head runbook: rules learned the hard way

Read this before any voice batch. Every rule below comes from a real failure on 2026-10-16/17 (Bailey ch2, 96 lessons).

## 1. Before the batch

- Ask the owner first: the Head renders everything itself (no workers, no approvals, about 6 hours per 100 lessons on
  Breeze), or workers (under an hour, but the permission check may refuse an upload). Exact question: CLAUDE.md.
  The rest of this runbook is for the workers choice.

- ⚠️🚨 Remind the owner about the `Kafu Voice` environment (CLAUDE.md warning) and check it with `list_environments`.
  Open every worker in it (`environment_id`), never in the default one.
- **First run in a fresh environment: ONE test worker first**, and wait until it has published its artifact with no
  message from the owner. Only then open the rest. (Opening 20 workers on an untested setup killed all 20.)
- Workers: `claude-haiku-5-5`, `permission_mode` auto, job inside the first message (`worker_prompt.py`), branch with the
  current tools (`source_revision`).
- Do not open new workers unless the owner says so. Do not "retry" a refused worker by opening another one.

## 2. Known failures and their fixes (all merged)

| Failure | Cause | Fix |
|---|---|---|
| `Setup script failed with exit code -1` | the environment kills its setup script after ~5 min | `voice_setup.py` detaches itself; the worker waits for `VOICE OK` |
| `Breeze failed:` (empty) or `AMX is not ready` | Breeze built with `-march=native`, container moved to another CPU | portable build (`-DGGML_NATIVE=OFF`, `src/build-portable`) |
| `Live-Shared Artifact Sensitive Delta` | worker uploading into the shared inbox | worker publishes a NEW private artifact of its own |
| `Untrusted Code Integration` / `Code from External` | worker reading its job from an artifact / installing from another branch | job inside the first message; install by the environment |
| `source_provenance_url_invalid:catalog_url` | export without `catalog_url` | `build_pkg.sh` takes `CATALOG_URL` and writes it |

## 3. When a worker is stuck

- A worker that waits for approval, or says its upload/publish was refused: **tell the owner at once**, the same turn,
  with the session links and one ready message to paste. Never wait for a scheduled check to do it.
- The Head cannot unblock it: workers correctly refuse messages from another session (`send_message`).
- Check a worker with `list_events` (`kinds: ["assistant","result"]`, `limit` 6). `list_sessions` without a filter is
  too big to read; parse the saved file for titles if you must.
- A stop-hook asking a worker to commit is noise: the worker must not commit (lean storage).

## 4. Collecting and building

1. `Artifact list` → new worker pages. `Artifact list scope files` → exact names. `Artifact read` with `paths`
   (DONE + parts) into a NEW folder per slot. Inbox ASSETS must be read one at a time (`path`); `paths` fails for asset ids.
2. Check every part's sha256 against `part_sha256` in DONE before importing.
3. `python3 -I tools/kafu_voice/import_voice.py DIR` → must print `IMPORT OK n lines (manifest n, failed [])`.
4. `tools/kafu_voice/build_pkg.sh EXPORT PKGID LESSONS OUT CATALOG_URL QID...` (≤12 lessons) → must show
   `"status": "PASS"` and the lesson count.
5. Send the ZIP to the owner with `SendUserFile` (attach) AND add it to the download page. Commit only
   `selection.json` + `lessons/*.lesson.json` under `work/<PKGID>/`.
6. One ZIP with everything is impossible: `package` splits anything over ~6 MB into parts itself. Say so instead of trying.

## 5. Talking to the owner

- Short Iraqi Arabic, numbers 1–100 (QID − 232 for Bailey ch2), never QIDs.
- If a word is ambiguous ("ادمج" = merge the git branch? or combine the ZIP files?), say in ONE line which meaning you are
  acting on before acting. On 2026-10-17 "ادمج" meant the ZIP files and the Head merged a PR instead.
- When the owner asks for a prompt for ChatGPT, write ONE master prompt that makes GPT write the image prompts; do not
  write the image prompts yourself.
- Report failures with the exact cause and who caused it. Never claim success that was not verified.
