# Kafu MotionCards — Project Brief

> **RETIRED (Oct 2026). Do not use this to make new content.** The owner stopped hand-animated MotionCards.
> New work is IMAGE LESSONS only: follow `motioncards/LESSON_PROMPT.md`. This file is kept only as background for
> the shared scaffold/package/validate tools.

> **SEPARATION WARNING:** This project is not Medical Motion. Nothing under `Animations and illustrations/` may be copied, imported, renamed, rebranded, or used as a runtime dependency.

## Product
Kafu MotionCards links independently authored browser-native educational animations to unchanged published MCQs. Authoring occurs outside the deployed app. The platform only validates, publishes, discovers and plays prebuilt packages.

Flow:

`kafu_mcq_text_export` JSON → select QIDs/count + durations → AI authors scenes using `motioncards/MASTER_PROMPT.md` → local tooling validates and packages → owner uploads `MCARDS_<PACKAGE-ID>_r<N>.zip` to the existing Telegram bot → isolated MotionCards publisher → students see a MotionCards control only on exact content-hash matches.

## Fixed identity
- Brand: **Kafu MotionCards**
- Root: `motioncards/`
- JS namespace: `KafuMotionCards`
- CSS prefix: `kafu-motioncards-`
- Action prefix: `motioncards-`
- ZIP `package_type`: `kafu-motioncards`
- Root manifest: `motioncards-manifest.json`

## Non-goals
- No deployed AI generation service or AI API subscription.
- No reuse of Medical Motion.
- No modification of MCQ question objects or QID allocation.
- No automatic generation during study.
- No storing MotionCards in the book publisher tree/state.
- No production rollout without owner review/approval.

## Security
Uploaded scene code is untrusted. Playback is sandboxed in a separate content origin using `sandbox="allow-scripts"` with host-owned controls and a bounded MessageChannel protocol. No Telegram initData, Kafu storage or user state enters the frame. Animation responses require restrictive HTTP CSP/security headers and no external network dependencies.

## Source binding
Every published animation binds to `book_id + book_version + chapter_id + qid + content_hash`. QID/fingerprint alone is insufficient because the publisher fingerprint excludes the answer. Hashes use the existing `kafu-question-canonical-json-v1` behavior against the original question object.

## Rollout
This branch may create deployment-ready configs/workflows and isolated tests. Merge, D1 migration application, service creation and production deployment remain owner-gated.
