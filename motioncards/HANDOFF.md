# Kafu MotionCards handoff

> **RETIRED (Oct 2026). Do not use this to make new content.** The owner stopped hand-animated MotionCards.
> New work is IMAGE LESSONS only: follow `motioncards/LESSON_PROMPT.md`. This file is kept only as background for
> the shared scaffold/package/validate tools.

> **SEPARATION WARNING:** Kafu MotionCards is a new independent system. Do not modify, import, copy, rebrand, or depend on `Animations and illustrations/`, Medical Motion, DNAgens, or their runtime code.

STATUS: PRODUCTION ROLLOUT ENABLED - FIRSTPROD TEST CARD REMOVED

## Production rollout completion — 2026-10-06

This section is the authoritative current production state. Older sections below are retained as historical review/audit notes and may describe pre-rollout conditions that are no longer current.

- PR #67 was merged to `main`; reviewed production merge SHA: `d4324fc2b902ac19ea0f8b99a61dc76916787bc2`.
- Authorized app/D1 rollout completed successfully in **Deploy Kafu run #48** (`37494302375`) on that exact SHA.
- D1 migration `0006_motioncards_queue.sql` applied successfully in run #48.
- App Worker staged version ID: `8dacc75c-0637-4181-a1b1-f553c0018417`; staged smoke, promotion, production smoke, and exact-production-SHA UI smoke all passed.
- First real package: `FIRSTPROD_r1`, QID `Q000007357`, package SHA-256 `1f0b703c612c811d98c356e45752513ffbcbacae06e2dfafd3f60b0ae19993c2`.
- Initial production promotion succeeded in MotionCards run #7; run #8 recovered the durable active pointer; run #10 reconciled and acknowledged the exact duplicate package with no redeploy.
- Owner remove/restore acceptance was exercised end-to-end in production:
  - run #14: remove published successfully;
  - run #16: restore published successfully;
  - run #18: final remove published successfully.
- Final production MotionCards state SHA-256 after run #18: `61ecfb101d975b3dc164e5ff0bb034db77eeb2991ad82123c4e105c408cfc836`.
- Final MotionCards tree SHA-256 after run #18: `a5cdda09ae4109de69e100f3668530fee49d237c26dd6d62e3bc5c0dd250ba03`.
- Final MotionCards Worker version ID from run #18: `6de7a9f5-ca34-48db-b816-9aaa258ccd64`.
- Final acceptance state intentionally has **0 active MotionCards**. `Q000007357` / `FIRSTPROD_r1` is soft-removed from students and remains recoverable from history.
- Run #18 production smoke: PASS with `active_cards: 0`, `removed_cards: 1`; production browser smoke: PASS; queue acknowledgement: PASS; ready queue count: 0.
- Owner explicitly enabled repository variable `MOTIONCARDS_ROLLOUT_ENABLED=true`.
- Gate verification run #19 (`37513105490`) was manually dispatched with both `initialize_state=false` and `production_authorized=false`. It executed successfully instead of being skipped, restored state `61ecfb...`, and returned `{"empty": true}`, proving normal enabled rollout behavior with an empty queue.
- Normal hourly recovery/drain and ordinary automatic app deployment are now enabled by the rollout gate. First-rollout manual authorization is no longer required for ordinary MotionCards publishing.
- Current production test posture: keep `FIRSTPROD_r1` removed; do not restore it unless intentionally testing restore again.

Key production runs:
- Deploy Kafu #48: https://github.com/blsmohamme972-lab/MCQs-Mountain-/actions/runs/37494302375
- MotionCards #10 first-package acknowledgement: https://github.com/blsmohamme972-lab/MCQs-Mountain-/actions/runs/37505787872
- MotionCards #14 remove: https://github.com/blsmohamme972-lab/MCQs-Mountain-/actions/runs/37510227904
- MotionCards #16 restore: https://github.com/blsmohamme972-lab/MCQs-Mountain-/actions/runs/37510944734
- MotionCards #18 final remove: https://github.com/blsmohamme972-lab/MCQs-Mountain-/actions/runs/37511701380
- MotionCards #19 enabled-gate empty-queue verification: https://github.com/blsmohamme972-lab/MCQs-Mountain-/actions/runs/37513105490

## Priority roadmap for the next AI/engineer

### P0 — Evaluate a 10,000+ daily-student, $0 MotionCards delivery model before scaling content

This is the **first architecture priority**, but it is a decision/review task, not a pre-approved implementation. A future AI/engineer must inspect the then-current code, Cloudflare free-tier limits, real usage telemetry and offline behavior before changing production. If a safer or more efficient design exists, prefer it and document why.

Primary candidate to evaluate:
- Make MotionCards **local-first with book/chapter downloads**: when a student downloads a chapter/book for offline study, also fetch the currently active MotionCards for that content and persist them locally (for example in the existing IndexedDB/offline download path).
- Prefer local playback after that first download so replaying a MotionCard does not create repeated network/Worker requests.
- Eliminate or materially reduce the current periodic MotionCards availability polling if it is no longer needed.
- Where compatible with the security model, evaluate serving immutable MotionCards/index assets as direct static assets so static delivery does not invoke Worker code unnecessarily.

The evaluation must compare this candidate against any better alternative that can realistically support **at least 10,000 daily students while keeping infrastructure at $0 or as close to $0 as practical**. Quantify request volume, D1 reads/writes, storage/file-count limits, download size, cache behavior, offline behavior and failure/recovery behavior before choosing the design.

Non-negotiable constraints:
- Keep MotionCards authoring/publishing independent from book publishing; downloading them together for the student must not make a book release responsible for MotionCards lifecycle.
- Preserve exact `book_id + book_version + chapter_id + QID + content_hash` binding.
- Preserve owner **Replace / Remove / Restore** safety and history. A locally cached card must not remain indefinitely trusted after the client reconnects and learns it is removed or replaced.
- Preserve sandbox/MessageChannel isolation and do not weaken CSP or source validation for offline convenience.
- Keep normal MCQ study usable offline even if MotionCards download/update fails.
- Avoid a design that requires one server request per question view or frequent background polling.
- Do not implement a large migration only because this note suggests one. First measure, compare alternatives, write the capacity calculation, and choose the smallest design that meets the 10,000-student target.

Expected output of that future review:
1. measured/current baseline;
2. 2–3 viable architectures with free-tier capacity estimates;
3. recommended design and reason;
4. migration/rollback plan;
5. tests proving offline playback, reconnect invalidation, Replace/Remove/Restore, and request-volume bounds.


## Repository state
- Branch: `feature/kafu-motioncards`
- PR: #67 (draft, owner review required before merge/deploy)
- Baseline/main inspected: `00f09cf42bbc021053ef95355bdad6b12f75e7b0`
- Latest relevant branch SHA at this handoff update: parent work through `d95f3edbf39a756134899ad54ee2157a7d83974e`
- Production merge/deploy/service creation/migration application: **NOT AUTHORIZED YET for this project**.

## Objective
Build an independent AI-authored, question-linked animation system:
published Kafu export -> selection/durations -> AI-authored MotionCards -> validation/package -> existing Telegram bot intake -> isolated publisher -> immutable MotionCards content origin -> exact question-linked player.

## Ownership map

### MotionCards-owned
- `motioncards/**`
- `motioncards-worker/**`
- `app/modules/motioncards-core.js`
- `app/modules/motioncards-player.js`
- `app/modules/motioncards.css`
- `worker/motioncards-queue.mjs`
- `tools/motioncards.py`, `tools/motioncards/**`, MotionCards tests/flows
- dedicated MotionCards workflow/config/state artifacts
- additive `motioncards_` D1 tables

### Shared integration
- `app/modules/manifest.json`
- minimal study/render integration via installed MotionCards player
- `worker/bot.mjs` document routing/internal MotionCards endpoints
- additive migration file
- `.github/workflows/ci-tools.yml`, `.github/workflows/ui.yml`
- dedicated `.github/workflows/publish-motioncards-queue.yml`

### Protected legacy / unrelated
- `Animations and illustrations/**` (Medical Motion)
- DNAgens and unrelated projects
- existing book queue/publisher/content state and `kafu-content-state`
- protected `KAFU-UPLOAD-TEST`
- existing CONTENT_SERVICE binding and MCQ export/cover fixes
- grading, attempts, leaderboard, FSRS, downloads, sync and book publishing behavior

## Implemented

### Source adapter / integrity
- Reads `kafu_mcq_text_export` schema v1 directly.
- Uses `questions[i].id/book_id/version/chapter_id`.
- Joins `export_metadata.question_integrity` by QID.
- Preserves original question objects; animation metadata is separate.
- Shared `kafu-question-canonical-json-v1` golden vector matches JS export core.
- Validates full content hash, publisher fingerprint contract, book/version/chapter identity.
- Correct answer extraction supports SBA, EMQ, multi and statement-by-statement MTF.
- Explicitly blocks unsupported answer encodings and image-dependent items whose bytes were not inspected.
- Regression covers the 30-record Upper Limb export mislabeled Whole book; derives the supplied chapter and never invents the other 179 records.
- Partition semantics do not confuse part count with aggregate export count.

### Selection / authoring kit
- Exact QIDs or deterministic first-N supplied records.
- Required integer duration_ms with per-QID overrides, 2-30s supported.
- Scaffold, preview, validate and package CLI.
- Declarative layers for labels, arrows, paths, highlights/focus, shapes and deterministic transitions.
- Optional custom renderer is bounded and rejects network/timer/eval/storage APIs.
- `MASTER_PROMPT.md`, `PROJECT_BRIEF.md`, `README.md`, `AGENTS.md`, `TOOLKIT.md`, examples and offline authoring bundle tooling exist.

### ZIP security / contract
- `MCARDS_<PACKAGE-ID>_r<N>.zip`; disjoint from book `_vN.zip` grammar.
- Root `motioncards-manifest.json`, package/runtime/protocol versions separated.
- Source records, editable scenes, compiled self-contained HTML and validation report.
- Entry/source/scene SHA-256 generated by tooling.
- Rejects traversal, absolute/noncanonical paths, Unicode/case collisions, symlinks, encryption, unsupported compression, CRC issues, bombs/ratios, executable/hosting files, missing/unapproved files and checksum/source-binding failures.
- Multipart preserves complete batch membership and complete animation boundaries.

### Player
- Availability index per book/version; local positive/negative cache; no D1/HEAD-per-question path.
- Exact match on book/version/chapter/QID/content_hash.
- No button for active timed exam; review modes remain eligible.
- Stable host is appended outside `#app`; background render does not replace active iframe.
- `sandbox="allow-scripts"` only.
- Host owns controls/timeline/final answer panel.
- MessageChannel protocol validates channel, QID and protocol.
- Child uses a deterministic `renderAt(time_ms)`; no independent timer loop controls scene motion.
- Host owns play/pause/seek/restart/end; final panel remains until replay/close and hides on backward seek.
- Current fix: compiled child now derives the random channel from iframe URL fragment so the ready handshake matches the host.

### Intake / publisher
- MotionCards filename router is isolated from legacy book parser.
- Owner/private-chat/webhook protections remain.
- Additive MotionCards queue tables and namespaced queue handler/internal operations.
- Dedicated MotionCards workflow/state/publisher tools.
- Publisher validates uploaded source binding against the actual approved published question source before activation.
- Same package bytes are no-op; same identity/revision with different payload conflicts.
- Intentional replacement required; unrelated mappings preserved.
- Dedicated static MotionCards Worker config/runtime with restrictive CSP/security headers and public allowlist only.
- No application auth secrets are intended in the content Worker.

## Test status

Latest completed CI before the current two fixes:
- Legacy Medical illustration job: PASS.
- MotionCards authoring/integrity/publisher/boundary tests: all PASS except one multipart split test.
- Visual flow: failed only because MotionCards child/host channel handshake never became ready.
- Failures were traced to implementation/test mechanics, not bypassed:
  1. child used a compile-time channel placeholder while host generated a fragment channel;
  2. multipart split target stayed fixed at 8MB when the test temporarily lowered archive limit.

Fixes now on branch:
- child derives validated 36-hex channel from `location.hash`;
- multipart split target respects the active ZIP ceiling;
- Content CI pull-request paths now include `motioncards/**` and `motioncards-worker/**`.

Current CI for these fixes: pending/not yet observed at this handoff update.

## Known owner-gated work
- Do not merge PR #67 yet.
- Do not apply migration 0006 to production yet.
- Do not create/deploy the production `kafu-motioncards` Worker/service yet.
- Do not operate the real Telegram upload queue for acceptance yet.
- Final production acceptance needs owner approval plus a real owner ZIP upload/question playback.

## Exact next action
Wait for/re-run CI on the handshake + multipart fixes. If green, inspect visual evidence and budgets, update this handoff with exact run IDs/results, and deliver the review report. If any check fails, fix the specific failure without weakening existing gates or baselines.

## Hardening milestone after owner audit

Reference SHA before this handoff update: `5fc9acfdbcfe75b2ce956945a1807d672e862280`.

Implemented on the existing PR/branch without merge/deploy:
- Local authoring preview now uses a trusted preview host with the real MessageChannel/timeline/final-panel contract. HTTP loopback is accepted only through the explicit preview compiler mode; production host-origin validation remains HTTPS-only.
- `tools/motioncards/smoke.py` is a reliable direct/module entrypoint with an explicit repository import path; workflow callers use `python -m tools.motioncards.smoke`.
- `motioncards-worker/wrangler.jsonc` sets `assets.html_handling: "none"`; the real Wrangler runtime acceptance verifies exact `.html` delivery without canonical redirect, Content-Type, CSP sandbox, Kafu-only CORS, immutable cache headers, byte hash, and browser handshake.
- Deterministic compiler validation rejects unfinished `EDIT:` takeaway placeholders and non-boolean replacement intent. Arrow heads now follow arbitrary arrow direction; transform rotation is rendered.
- Duplicate publication returns a stable `package_sha256`/changed contract. Queue finish with `duplicate:true` acknowledges the queue/publication record without card upserts, so it cannot reactivate a removed card or overwrite a newer replacement.
- Downloaded queue identity validation requires filename/group/manifest package ID+revision, multipart indexes/totals, complete membership, and exact downloaded sizes before publishing.
- MotionCards queue uses expiring lease tokens, stale-finish rejection, bounded attempts, continuation dispatch, hourly recovery, and preserves valid multipart parts during repair.
- Owner management is implemented through `/motioncards QID`: trusted Preview, Replace guidance, reversible Remove, and compatible-version Restore. Replacement activation requires expiring owner/private-chat confirmation bound to candidate digest and expected active package/revision/digest.
- Soft remove/restore uses the same state candidate/deployment pipeline; unrelated cards remain intact. Student availability refresh remains bounded to 35 seconds in production and is now explicitly exercised on an already-open question.
- Player lifecycle now binds account + study-session instance + book/version/chapter/QID + full content hash. It cancels its RAF before teardown, blanks the stale iframe, pauses on visibility/page exit, has a real Retry action, focus trapping/restoration, stale-channel rejection, and rapid-reopen/session-switch coverage.
- Initial publication recovery now distinguishes durable-but-unpromoted candidates from active state. A verified pending candidate can rebuild an empty retry base without becoming active; multiple ambiguous candidates fail closed. Generic repository/auth 404s are no longer treated as proof that the state release is absent.
- State candidate restore verifies state/tree/artifact hashes and uses safe tar extraction; candidate artifacts remain immutable.
- Package validation checks full nested contracts, exact source identity/duration/final panel, current published source membership at publication, and rebuilds deterministic compiled entries from validated scene source to compare exact bytes.
- Existing real asset-routing acceptance is preserved and strengthened with Kafu-only asset CORS.

Current production status:
- No merge to main.
- No production migration applied.
- No MotionCards service created/deployed by this hardening work.
- No real Telegram production queue operation performed.
- No secrets or credentials changed.

Next exact action:
Run full Content Contract CI and Visual/Flow CI on the current branch head. Fix only reproducible failures tied to this hardening, then update this handoff/README/MASTER_PROMPT/PR description with exact run IDs and remaining owner-gated blockers.

## Owner-audit hardening verification

Runtime/code verification SHA: `873b374244bcecdfcb4c74a6a9d1d33f53b231bb`.

Verified on that SHA:
- Kafu Content Contract CI: SUCCESS — run `37458775325`.
- Kafu Visual and Flow CI: SUCCESS — run `37458775180`.
- Legacy Medical illustration job inside Content CI: SUCCESS.
- Built-app MotionCards journeys: SUCCESS, including rapid reopen, stale-message rejection, background pause, Retry after a transient failed child load, same-QID new-session isolation, full-identity/account isolation, and soft-remove propagation on an already-open question.
- Real Wrangler static-asset acceptance: SUCCESS with the actual `motioncards-worker/wrangler.jsonc`; exact immutable `.html` returned 200 without canonical redirect, correct Content-Type, CSP/sandbox, Kafu-only CORS, cache headers, exact entry SHA-256, and MessageChannel ready/intermediate/end playback.
- Fresh offline authoring kit subprocess: scaffold -> edit -> trusted preview host -> package -> validate: SUCCESS.
- State recovery tests: release lookup fail-closed, safe extraction, immutable candidates, initial promotion interruption, durable unpromoted candidate retry-base recovery, ambiguous candidate rejection: SUCCESS.
- Publisher/intake tests: duplicate publication no-op contract, source revalidation, targeted replacement confirmation/staleness, remove/restore, multipart completeness/identity, leases/retries/drain: SUCCESS.

Failure-before evidence observed during this hardening:
- local preview rejected the loopback origin and direct child links were not a usable player;
- direct `tools/motioncards/smoke.py` had an import-path dependency;
- Cloudflare HTML routing had no explicit `html_handling:none`;
- candidate verification had a Path-expression bug;
- duplicate recovery could feed cards back into queue finish;
- Retry changed only the URL fragment and could reuse the failed child document instead of issuing a new asset request;
- queue tests contained malformed template-literal escaping and null-prototype assertion mismatches.
Each reproduced failure was fixed without disabling a gate or updating a visual baseline to hide it.

Documentation-only follow-up commits after the tested runtime SHA update README, MASTER_PROMPT, owner management instructions and this handoff. Re-run CI on the final documentation head before reporting final review status.

### Owner demonstration after authorized deployment

1. In the private owner chat send `/motioncards Q000000001`.
2. Tap **Preview**: it opens the trusted Kafu host player.
3. Tap **Replace** and upload a validated ZIP containing only the intended replacement card(s). Review the exact replacement list and confirm it; stale confirmation must be rejected.
4. Tap **Remove from students** and confirm. After successful publication, the student's button disappears within the documented bounded refresh window (public index max-age 30s; app refresh 35s by default).
5. Re-open `/motioncards QID`, choose **Restore previous compatible version**, and confirm. Only that QID is restored after source revalidation; unrelated newer cards remain intact.

### Remaining owner-gated blockers

- PR #67 remains Draft/Open and unmerged.
- Migration 0006/any MotionCards production migration has not been applied.
- The production `kafu-motioncards` service has not been created/deployed by this review work.
- The real Telegram production queue has not been operated.
- Final production acceptance still requires explicit owner approval followed by a real owner ZIP upload and student playback.

## Follow-up queue/recovery audit hardening

Code verification SHA before this handoff documentation update: `8bf03c2c22cb61b18f9d843f1cbfc2baafff11cb`.

The follow-up audit reproduced four remaining control-plane failures against the current queue/migration logic: lost first acknowledgement left D1 management/history absent, expired replacement confirmation could strand an `awaiting_confirmation` group, concurrent intake could overwrite an occupied part, and clear could race a retry/claim. These cases now have repository regressions using the real MotionCards queue functions and the actual SQLite migration.

### Durable publication reconciliation
- Durable MotionCards `state.json` remains the publication-side source of truth; D1 is the management/control-plane projection.
- On a duplicate retry after publication, the publisher emits a management reconciliation snapshot from the **current durable state**, not from the old upload. It includes each affected card's current active/removed state and relevant compatible version history.
- The queue finisher applies that snapshot only when the exact group/digest has no prior publication acknowledgement. An already-acknowledged duplicate remains a no-op for card mappings.
- This recovers a lost first acknowledgement without another content deployment and cannot resurrect a removed card or downgrade a newer replacement.
- Lost remove/restore acknowledgements use the same current-state reconciliation rule.

Verified regressions in Content CI run `37468259832`:
- `lost first MotionCards acknowledgement reconciles cards and history from durable current state` — PASS.
- `lost replacement acknowledgement converges to durable active revision and history` — PASS.
- `already acknowledged duplicate cannot resurrect removed card or downgrade newer replacement` — PASS.
- `lost remove and restore acknowledgements reconcile from durable operation state` — PASS.

### Expired replacement confirmation recovery
Owner flow:
1. Re-open `/motioncards QID` after the 15-minute confirmation expired.
2. The pending replacement is shown with **Renew confirmation** and **Cancel replacement**.
3. **Renew confirmation** invalidates outstanding old tokens, requeues the already accepted parts, revalidates the package/source and the **current** active package/revision/digest, then issues a fresh confirmation.
4. **Cancel replacement** invalidates the pending token and cancels only that candidate; the active student card is unchanged.
5. Command equivalents: `/motioncards-retry PACKAGE-ID_rN` renews an awaiting replacement; `/motioncards-clear PACKAGE-ID_rN` cancels it.
6. A failed Telegram notification after durable confirmation creation is non-fatal; the owner can recover from `/motioncards QID` or status.

Old/used/cancelled/stale tokens fail closed. Renewal also fails closed if the active card changed after the original candidate was prepared.

Verified regressions in Content CI run `37468259832`:
- expired confirmation renewal/revalidation/cancellation — PASS.
- confirmation notification failure remains recoverable — PASS.

### Concurrent intake / clear
- Part writes are guarded inside D1 transactions rather than relying on preflight reads alone.
- Identical duplicate intake is idempotent and does not dispatch twice.
- A different payload cannot replace an occupied part once another request wins.
- Running, awaiting-confirmation and published groups reject part mutation.
- Failed-part repair remains conditional and preserves other valid parts.
- Clear guards both child-part and parent-group deletion against the current failed state; a claim/retry race leaves current running work untouched.
- Claims/finish remain lease-token protected; stale leases cannot publish cards or publication records.

Verified regressions in Content CI run `37468259832`:
- concurrent different-file same-part intake — PASS.
- intake/claim and clear/claim deterministic races — PASS.
- concurrent failed repair has one winner — PASS.
- expired lease cannot publish — PASS.
- multiple ready uploads remain claimable without another upload — PASS.
- failed multipart repair preserves accepted valid parts — PASS.

### Full review verification on code SHA 8bf03c2
- Kafu Content Contract CI: SUCCESS — run `37468259832`.
- Kafu Visual and Flow CI: SUCCESS — run `37468259892`.
- Worker queue suite: 47 pass / 0 fail.
- Real Wrangler MotionCards static-asset/browser runtime: PASS, including exact immutable HTML route, security headers, entry SHA-256, and ready/intermediate/end MessageChannel playback.
- Existing MCQ export, content binding, D1/read-bound checks, built-app flows and legacy Medical Motion job remained green.

### Verification boundaries
- The queue/race regressions are integrated local SQLite/D1-compatible tests using the repository's actual migration and queue functions; they are not a production Cloudflare queue execution.
- Wrangler static-asset/player verification is a real local Wrangler runtime, not a mocked `ASSETS.fetch` response.
- No production migration, MotionCards service creation/deployment, credential change, real Telegram queue operation, merge, or production acceptance occurred.

### Current status / next action
- PR #67: Draft/Open for owner review.
- Branch: `feature/kafu-motioncards`.
- No merge or deployment is authorized in this task.
- Next action: owner reviews this hardened PR. If approved later, obtain explicit production authorization before applying MotionCards migrations, creating/deploying the MotionCards service, or operating the real owner queue.

## Confirmation atomicity hardening

Reviewed/audited input head: `6d4cac0010a0a686193e40433184d3d46d02b030`.

Failure-before evidence:
- Audit harness reproduced the race on replace/remove/restore: queue mutation changed 1 row while token-consumption changed 0 rows after expiry/invalidation between preflight and the batch.
- Repository regressions were added **before** the fix against the real `confirmMotioncardAction()` and migration `0006_motioncards_queue.sql`.
- Content CI run `37475150809` failed exactly on those new atomicity cases while the unrelated legacy Medical Motion job remained green.

Implemented correction:
- Confirmation preflight remains only for readable errors; authorization no longer relies on it.
- Replace transition now guards the group mutation inside SQL on owner/chat identity, token unused/unexpired state, candidate digest, awaiting-confirmation state, and every current active target's digest/package/revision.
- Confirmed replacement authorization stored on the group is bound to the exact confirmation token plus target map. The queue worker unwraps this envelope backward-compatibly before publisher validation.
- Remove/restore operation insertion is now an `INSERT ... SELECT` directly from an eligible confirmation joined to the current card. It validates owner/chat, expiry/unused status, current active digest, book/version/chapter identity, and for restore the requested historical target row.
- Token consumption is guarded by the transition created by that exact token. If expiry, invalidation, cancellation/renewal, candidate change, or target change wins before the transaction, both writes are no-op and no executable work is created.
- Concurrent duplicate callbacks remain single-use and idempotent.

Repository regressions cover all three operation kinds:
- valid confirmation;
- owner/chat mismatch;
- expired before read;
- expiry after preflight/before transaction;
- used/invalidation after preflight;
- changed current target after preflight;
- duplicate callback;
- replacement candidate-digest race;
- replacement concurrent renewal/cancellation.

### Merge/deployment safety

Merge is **not** production-neutral in this repository:
- `deploy-app.yml` watches matching pushes to `main`, applies remote D1 migrations, and promotes the app Worker.
- `publish-motioncards-queue.yml` has an hourly schedule.

Review-only gating changes are now prepared without changing any production setting:
- `MOTIONCARDS_ROLLOUT_ENABLED` defaults effectively false/unset.
- `deploy-app.yml` stops before remote migration/deployment while the gate is false unless manually dispatched with `motioncards_rollout_authorized=true`.
- Scheduled MotionCards publishing is skipped while the gate is false.
- Manual pre-gate MotionCards publishing requires `production_authorized=true`.
- Gate behavior has repository regression coverage in `tools/tests/test_motioncards_rollout_gates.py`.

The exact authorized first-rollout sequence is documented in `docs/ADMIN.md`. No repository variable, production workflow, migration, service, credential, or real queue has been changed/operated in this review work.

### Current status

STATUS: READY FOR OWNER REVIEW - DO NOT MERGE OR DEPLOY

Final verified review-code head before this handoff-only update: `ae94f19f58321c22b0efac1bdc1dc914110357eb`.

Verification on that head:
- Kafu Content Contract CI: SUCCESS — run `37476869185`.
- Kafu Visual and Flow CI: SUCCESS on rerun attempt #2 — run `37476869576`.
- Visual attempt #1 on the same SHA failed only on `ipad-dark-library-no-results`; no app/visual code or baseline changed, and rerun #2 passed main journeys, approved comparisons, real MotionCards Wrangler routing/handshake, budgets, and evidence generation.
- Confirmation atomicity repository suite: replace/remove/restore valid, owner/chat mismatch, pre-expired, post-preflight expiry, post-preflight invalidation, changed target, duplicate callback, candidate-digest race, and renewal/cancellation race all PASS.
- Worker queue suite: 64 pass / 0 fail.
- MotionCards rollout-gate tests: PASS.
- Legacy Medical Motion job: PASS.

Failure-before evidence:
- Content CI run `37475150809` failed the newly added confirmation atomicity regressions against the pre-fix implementation. In the reproduced race, a rejected callback could leave executable replacement/remove/restore work committed because the queue mutation changed one row while token consumption changed zero.

Atomicity invariant after the fix:
- Queue authorization and token eligibility are coupled inside guarded SQL executed in one D1 batch transaction.
- A token that expires, is used/cancelled/renewed, loses owner/chat eligibility, points at a stale candidate, or sees a changed active target before the transaction produces no executable operation and does not authorize a replacement.
- Valid confirmations remain single-use and idempotent.
- Existing Renew/Cancel, durable-state reconciliation, intake/clear protections, player behavior, source validation, and legacy separation remain intact.

Rollout boundary:
- Merge is not production-neutral. `deploy-app.yml` can apply remote D1 migrations and promote the app after matching pushes to `main`; the MotionCards publisher has an hourly schedule.
- Reviewed fail-closed gates are present, but no repository variable or production setting was changed during review.
- The exact first-rollout sequence is documented in `docs/ADMIN.md`.
- No merge, deployment, production migration, MotionCards service creation, credential change, repository rollout-variable change, or real production queue operation occurred.

Next action:
- Owner reviews PR #67.
- If the owner wants production rollout later, obtain explicit production authorization covering the documented rollout sequence before merge/manual deployment/service creation/migration/publisher enablement.

## Between-statements confirmation expiry + production-smoke alignment

Reviewed input head: `6acaebb70ebb7c8b78d6faa0f0ca18093a738121`.

### Failure-before evidence

The supplied read-only audit bundle imports the unchanged real `worker/motioncards-queue.mjs` and loads migrations `0001` through `0006` into isolated Node SQLite. It delays only wall-clock time between the two statements inside one `BEGIN IMMEDIATE / COMMIT` transaction.

Against the reviewed head it reproduced for replace/remove/restore:
- first guarded mutation changes: 1;
- later token-consumption changes: 0 after expiry;
- callback returns rejected;
- executable work remains committed;
- token `used_at` remains null.

Independent local rerun of that audit produced `REJECTED_BUT_EXECUTABLE=3`.

Repository regression `MotionCards <kind> confirmation uses first guarded transition as expiry linearization point` was added before the fix. On the test-only SHA `a56a5a17c3accc96023edc59dfc517852ea09b3a`, Content CI job `112332752999` failed exactly three cases: replace, remove and restore. The earlier preflight/before-batch protections remained green.

Rollout mismatch was also captured before the workflow fix. Content CI run `37482231724` failed the new rollout assertions because `ui.yml` still required `production_smoke.py --commit "$GITHUB_SHA"` on every matching main push while `deploy-app.yml` intentionally blocks unauthorized first rollout.

### Confirmation acceptance timing

The explicit linearization point is now **the first guarded database transition**:
- for replace: the guarded `motioncards_groups awaiting_confirmation -> ready` update;
- for remove/restore: the guarded `INSERT ... SELECT` that creates the exact ready operation.

That first transition evaluates expiry together with owner/chat identity, token unused state, candidate/current-target identity and operation-specific validation.

The second statement consumes the exact token only if the exact transition artifact created by that token exists. It intentionally **does not evaluate wall-clock expiry again**. Therefore a token valid at the accepted first transition cannot be retroactively rejected merely because wall-clock time advances before token consumption. This does not extend token life: a token already expired at the first transition changes zero rows and creates no executable work.

Token consumption still requires the same token, owner/chat, unused state and exact transition binding; zero-row consumption is still a failure. Renew/Cancel and stale-target protections remain unchanged.

### Runtime evidence boundaries

- **SQLite fault injection:** deterministically crosses expiry between statements by sleeping inside the local batch adapter. This is the boundary regression and is not production D1 evidence.
- **D1-compatible local runtime:** `tools/tests/motioncards-d1-runtime.mjs` uses Miniflare/workerd with the real migration and real queue module. It verifies valid confirmation consumption and pre-expired rejection in addition to the existing concurrency/reconciliation controls. It does not claim deterministic wall-clock delay injection between D1 batch statements.
- **Production:** no production D1, queue or Telegram confirmation was exercised in this review task.

### Production smoke / rollout gate alignment

- `.github/workflows/ui.yml` keeps local/built Visual/Flow, browser, budget and Wrangler checks but no longer waits for a production SHA on a matching main push.
- `.github/workflows/deploy-app.yml` owns the exact-production-SHA browser smoke after successful promotion and normal production smoke.
- Gated merge with rollout disabled: local CI can pass; app deployment is intentionally blocked before remote writes; exact production SHA check is not run.
- Authorized first rollout: manual `deploy-app.yml` with `motioncards_rollout_authorized=true` must deploy first, then run exact SHA smoke.
- Normal enabled rollout: matching main pushes deploy and retain the same exact SHA post-promotion smoke.
- Failed deployment: the later exact-SHA step is not executed and must not be reported as PASS.

Detailed expected statuses and first-rollout sequence are in `docs/ADMIN.md`.

### Current status

STATUS: READY FOR OWNER REVIEW - DO NOT MERGE OR DEPLOY

Final verified review-code head before this handoff-only update: `cf7dd5233d8e60f205f8e76442dcd93f36cb4d7e`.

- Kafu Content Contract CI: SUCCESS — run `37486905242`.
- Kafu Visual and Flow CI: SUCCESS — run `37486905333`.
- Worker queue suite: 67 pass / 0 fail, including replace/remove/restore between-statements expiry-boundary regressions.
- Miniflare/workerd D1-compatible runtime: PASS, including valid confirmation consumption and safe pre-expired rejection. The deterministic between-statements wall-clock fault injection remains SQLite-specific evidence and is not claimed as a production-D1 reproduction.
- Rollout production-smoke gate tests: PASS.
- Main journeys/approved visual comparisons: PASS.
- Real MotionCards Wrangler static-asset routing and sandbox handshake: PASS.
- Legacy Medical Motion job: PASS.
- PR #67 remains Draft/Open and unmerged.
- No merge, deployment, production migration, service creation, credential/variable change, rollout-variable change, or real production queue operation occurred.
- Next action: owner reviews PR #67. Any production rollout still requires separate explicit authorization and the documented sequence in `docs/ADMIN.md`.


## Scene engine v2 (2026-10-07)

### Why

v1 scenes looked flat and robotic. The causes were in the engine, not in the authoring model:
- `scale`/`rotate` pivoted around the canvas origin, so animated shapes slid diagonally;
- interpolation was linear only, with no easing;
- `start_ms/end_ms` defined both visibility and tween length, so "appear quickly, then stay" was impossible;
- there were only two states (`from`/`to`);
- there were only 7 primitives, with no gradients, groups, drawn-on strokes, motion along a path, particles or text wrapping;
- authors drew blind, with no rendered feedback.

### What changed

- `motioncards/lib/engine_v2.py`: strict validator, layout linter and deterministic runtime for scenes that declare `"schema_version": 2`. It adds:
  - easing and keyframes;
  - `show` separate from `keys`, and enter/exit presets;
  - pivots on each shape's own centre;
  - path morphing and drawn-on strokes;
  - `along` paths, `particles`, `spotlight` and a camera, with `fixed` HUD layers;
  - wrapped, auto-fitting text with label boxes;
  - gradients, shadows and glow;
  - validated PNG/JPEG/WebP data-URI assets;
  - colour tokens, groups, `repeat`, and a hardened `custom_renderer` with `h.el`.
- `compiler.py` dispatches on `schema_version`. **The v1 path is untouched and byte-identical**: golden hashes are pinned in `tools/tests/test_motioncards_engine_v2.py`, so every previously built v1 ZIP still passes the publisher's rebuild-and-compare check.
- Unchanged:
  - the host/iframe protocol (1);
  - the manifest/index `runtime_version` (1);
  - the app player;
  - the MotionCards Worker CSP;
  - the bot;
  - D1, the queue and the publisher.

  No app, Worker or bot deployment is needed for v2. Only the validator/compiler code that the publisher workflow checks out from `main` must contain v2 before a v2 ZIP is uploaded.
- `motioncards/lib/render.py` plus `tools/motioncards.py render|lint`:
  - renders scenes through the real sandboxed MessageChannel protocol under the production entry CSP;
  - writes phone/tablet PNG frames and a contact sheet;
  - fails on a card render error or a non-deterministic seek.
- Scaffold now writes v2 starter scenes (`--schema 1` keeps the legacy starter). v2 rejects leftover `EDIT:` text.
- Authoring docs:
  - `AUTHORING_V2.md` is the compact reference the AI reads;
  - `examples/v2-stenosis-flow.scene.json` and `examples/v2-synapse-steps.scene.json` are the gold examples;
  - `MASTER_PROMPT.md` points to these and adds the lint/render steps;
  - the authoring kit bundle includes the new files.
- CI: new `motioncards_engine` job (Playwright 1.57.0 + Chromium) runs the browser tests.

### Verified in the cloud session

- MotionCards Python tests: 58/58 pass on Python 3.13, including the browser tests. On Python 3.11 the browser tests skip without Playwright and the rest pass.
- Compiled bytes are identical across Python 3.11, 3.12 and 3.13, so ZIPs built in any authoring environment match the publisher's rebuild.
- `tools/motioncards/browser_smoke.py` (the publisher's own post-deploy check, unmodified) passes for v1 and v2 entries served with the exact production CSP. HTTPS staging was simulated locally because this sandbox blocks outbound network.
- The full authoring-kit flow (bundle → extract → scaffold → lint → render → package → validate) passes from a clean extracted kit.
- The four non-MotionCards failures in the local full suite (`test_frontend_modules` ×2, `test_service_worker_build`, `test_design_style` fonts) are pre-existing. They need `cdn.jsdelivr.net`, which this sandbox's network policy blocks, and they fail identically without this change.

### Free mode and removal of the identifier blacklist (2026-10-07, follow-up)

Honest correction of the first v2 iteration: a large custom JSON DSL is itself a constraint, because models are far more fluent in plain SVG and JavaScript. The `custom_renderer` identifier blacklist (`window`, `document`, `self`, …) was also security theatre: the real boundary is the sandboxed, opaque-origin iframe plus the network-less CSP.

- v2 scenes may now include `svg` (any well-formed SVG markup) and `script` (plain JavaScript with full DOM access inside the sandbox; `function render(t, api)` plus an optional `setup(api)`). Layers become an optional shortcut, and the two can be mixed.
- Rejected only where something would otherwise break or silently fail:
  - `</script`, `<script` or `<!--` in code (they end the page's script element; reported with line number);
  - malformed SVG (reported with line and column);
  - `<script>` inside `svg`;
  - external `href`/`url()` (blocked by CSP in production);
  - unknown `asset:`/`@token` references.
- Runtime guards that prevent pause/seek bugs without failing the card:
  - timers and `requestAnimationFrame` are inert, with a one-time console note;
  - `Math.random` is seeded;
  - the runtime runs in an IIFE, so author globals cannot collide with runtime names (tested).
- Errors carry their location, e.g. `script line N`, `render(t=…)`, or SVG line/column. They are surfaced by `motioncards render`, which now checks determinism on the visible DOM (exact) instead of screenshot pixels (paint-timing flaky).
- New gold example `examples/v2-free-o2-curve.scene.json`: the O₂–Hb dissociation curve computed from the Hill equation (n = 2.7; P50 26.8 → 35 mmHg). Saturations at tissue PO₂ 40 are computed (75% → 59%), not drawn by eye.
- Verified:
  - all MotionCards tests pass on Python 3.13 with browser tests, and on Python 3.11 without them;
  - compiled bytes are identical on Python 3.11 and 3.13;
  - unmodified `browser_smoke.py` passes for 6 entries (2 v1, 4 v2) under the production CSP;
  - the clean-kit flow scaffold → lint → render → package → validate passes for the free-mode example.

### Imported illustrations and 3D evaluation (2026-10-07, follow-up)

- `motioncards/lib/assets.py` plus `tools/motioncards.py import-svg FILE|URL --scene … --id … --box … [--template] [--credit …]`:
  - cleans third-party SVG: removes DOCTYPE, metadata, editor namespaces and event handlers, and rejects external links/CSS;
  - fits it into a stage box, or into a `<defs>` template for `<use>`;
  - prefixes every id and CSS class, so multiple imports never collide;
  - rounds coordinates without merging compact numbers;
  - records `credits`, which the runtime prints small in the card corner (CC BY attribution).
- Tested with real Servier Medical Art and Bioicons files (heart, heart interior, lung, erythrocyte, neuron): five imports render together with no collisions.
- New gold example `examples/v2-imported-art-sickle.scene.json`: the model-authored part is about 1.15k tokens; the imported art never enters the model context.
- Validator gap fixed: `<style>` with `@import` or external `url()` inside `svg` is now rejected.
- 3D: three.js r150 (614 KB) runs inside a card under the production CSP and sandbox (WebGL OK in headless Chromium).
  - It costs about 640 KB per card.
  - The DOM determinism check does not cover canvas pixels.
  - A model-invented "biconcave" shape came out anatomically wrong in the test.
  - Documented as possible but rarely worth it.
- Measured token cost per card (characters/3.6):
  - v1 examples: 300–410;
  - v2 cards: 1.1k–2.2k;
  - `AUTHORING_V2.md` read once per session: about 3.8k.

  v2 cards are therefore larger than v1 cards. The gains are in quality, in errors caught locally with their location, and in imported art costing about 0 tokens instead of 8k–25k.

### Research-backed adjustments (2026-10-07, follow-up)

Web research findings and what was changed:
- **Image input helps:** Graphic-Design-Bench (arXiv 2604.04192) shows image-conditioned SVG fidelity well above text-only. This supports keeping the `render` visual loop mandatory.
- **AI-written Lottie stays out:** the same benchmark scores AI-written Lottie animation poorly (best 0.598), so Lottie stays out of AI authoring.
- **Organic morphing stays out:** LiveSVG (arXiv 2605.30174) and VAnim report that language models handle rigid transforms but not non-rigid organic deformation.
  - `AUTHORING_V2.md`: never morph complex organic outlines; cross-fade between real drawings instead.
  - `lint`: warns when a keyed path morph has more than 60 numbers.
- **Licences per source:**
  - NIH BioArt Source: mostly public domain, but the licence is set per entry and includes NC/ND variants.
  - Servier: CC BY 4.0 on the official site; the Bioicons mirrors carry CC BY 3.0.
  - Reactome Icon Library: CC BY 4.0.
  - Health Icons: CC0.
  - All four are documented with credit wording.
- **NC/ND licences refused:** `import-svg` refuses any NC/ND credit, because cards are derivatives and the app may be paid. `lint` flags NC/ND credits added by hand.
- **Not adopted:**
  - 3D anatomy (Z-Anatomy, CC BY-SA, with upstream BodyParts3D licence doubts, no glTF and uncertain project status);
  - GSAP (its free licence asks for a paid business licence when end users pay).
- **Offline open item:** Telegram iOS WebView offline storage remains a device-test item before any offline MotionCards work.
- Tests: all MotionCards tests pass on Python 3.13 with browser tests, and on Python 3.11 without them.

### Everyday art sources (2026-10-08, docs only)

- Everyday art now starts with Servier itself: bioicons `General_items`/`Animals`/`Plants_Algae` SVGs (S1) and the SMART PowerPoint sets (S2, CC BY 4.0: People, Risk-Factors, Dietetics, …). The new `tools/motioncards_smart.py` lists and extracts single drawings from a SMART set as cropped SVG (LibreOffice → PDF → `pdftocairo` → crop in Chromium). Houses, rivers and landscapes remain a gap: IAN/UMCES symbols cover them but are CC BY-SA (owner decision).
- Emoji sets are demoted to small props: (E1 Fluent Emoji MIT, E2 Noto Emoji 2D Apache 2.0, E3 Twemoji CC BY 4.0, E4 Kenney CC0 vector packs, E5 Open Peeps CC0), a "maybe" list and a "Do not use" list. Licences were read from each project's own file or page on 2026-10-08; samples were imported and rendered.
- Found: `import-svg` drops attributes on the root `<svg>`, so Figma exports with root `fill="none"` (Fluent Emoji) render black blobs. The doc gives a wrap-in-`<g fill="none">` workaround; fixing the importer is a separate change.
- The three temperature recipes (`R.thermometer`, `R.sweat`, `R.arrowGrow`) were added to the Recipes table.
- No library art was added: library entries need `used_in` card QIDs.

### Voice-over on by default, free unlimited card delivery (2026-10-08)

- **Delivery:** `motioncards-worker/_headers` replaces `run_worker_first`, so card and index views are static-asset requests: free, unlimited, and off the shared 100k/day Worker quota. Headers are byte-identical (real Wrangler runtime PASS). The publish workflow refuses to deploy without `_headers`.
- **Package:** `motioncards.py package` requires `work/<batch>/voice/<QID>.opus` (from `voiceover/voiceover.py make`) unless `--no-voice`. The validator checks the voice strictly (Ogg Opus, ≤64 KB, SHA-256, real length, cues). The v2 compiler embeds it; the card hands the exact bytes to the host after `ready`. The index carries `voice {mime,bytes,sha256,track_ms}`.
- **App:** `modules/motioncards-voice.js` plus player wiring. The verified voice plays on the Play tap and is the master clock, with a mute button (remembered). A mismatched voice is never played.
- **Left:** shard Workers before about 20,000 published cards; an optional WASM decoder for iOS before 18.4 (those phones play the card silently today). See `voiceover/PLATFORM_PLAN.md`.
