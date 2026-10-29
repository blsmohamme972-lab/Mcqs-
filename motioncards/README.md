# Kafu MotionCards

> **RETIRED (Oct 2026). Do not use this to make new content.** The owner stopped hand-animated MotionCards.
> New work is IMAGE LESSONS only: follow `motioncards/LESSON_PROMPT.md`. This file is kept only as background for
> the shared scaffold/package/validate tools.

> **GOLD STANDARD (read first):** follow [`GOLD_STANDARD.md`](GOLD_STANDARD.md), the owner-approved workflow, card format and visual method from MRCS chapters 20–25.

> ## ⛔ Independent project — do not use the legacy animation library
> Kafu MotionCards is **not** `Animations and illustrations/` / Medical Motion. Do not modify it, import it, copy components from it, rename it, rebrand it, or make MotionCards depend on it.

This directory contains the authoring contract, schemas, runtime protocol, CLI tooling, fixtures, examples, validation rules and durable handoff for Kafu MotionCards.

The intended owner workflow is:

1. Export published MCQs from Kafu.
2. Give an AI agent that JSON plus exact QIDs/count and durations.
3. The agent reads `MASTER_PROMPT.md`, scaffolds MotionCards, previews and validates them.
4. The tooling calculates source/artifact hashes and builds `MCARDS_<PACKAGE-ID>_r<N>.zip`.
5. The owner uploads that ZIP to `@KafuMcqsbot`.
6. The isolated MotionCards publisher validates source provenance and publishes immutable assets/indexes.
7. The Kafu study screen shows MotionCards only when the current unchanged question matches the published binding.

Development and content authoring are deliberately separate. Content-generation agents must not modify platform code merely to author a batch.

See `PROJECT_BRIEF.md`, `AGENTS.md`, `MASTER_PROMPT.md`, and `HANDOFF.md`.

**Authoring new cards:** use scene schema v2. `AUTHORING_V2.md` is the compact reference, and `examples/v2-*.scene.json` are the gold examples. Check every card with `python tools/motioncards.py lint --workspace …` and look at it with `python tools/motioncards.py render --workspace … --out …` before packaging. Legacy v1 scenes keep working unchanged.

## Owner management

Published MotionCards are managed through the existing private owner bot; do not edit hashes, release assets, or D1 rows manually.

- Send `/motioncards Q000000001` to inspect the current card.
- **Preview** opens the trusted Kafu host player, not the raw child HTML entry.
- **Replace** tells you to upload a ZIP containing only the intended replacement card(s). The candidate is fully validated first; if it would replace active cards, the bot lists the exact QIDs and requires an expiring confirmation bound to the owner/private chat, candidate digest, and expected active package/revision/digest.
- **Remove from students** is a reversible soft-unpublish. It removes only that card from the published availability mapping.
- **Restore previous compatible version** revalidates the current published question binding before restoring only that QID. It does not roll back unrelated later uploads.

The student availability index is served with a 30-second cache and the app performs a bounded refresh cycle (35 seconds by default), so a removed card disappears from an already-open compatible question within that documented window after a successful publication. This does not promise deletion of bytes already present on an offline client.

Replacement, removal, and restoration use the same candidate/state/deployment pipeline as ordinary MotionCards publishing.

### Expired replacement confirmation

Missing the 15-minute replacement confirmation does **not** require rebuilding the ZIP or incrementing its package revision.

- Re-open `/motioncards QID`. A card with a pending replacement shows **Renew confirmation** and **Cancel replacement**.
- **Renew confirmation** invalidates every old open token for that candidate, requeues the already accepted ZIP parts, revalidates the package/source and the **current** active package/revision/digest, then issues a fresh confirmation. If the active card changed meanwhile, renewal fails closed as stale.
- **Cancel replacement** invalidates the old token and cancels only the pending replacement. The active student card is not removed or changed.
- Command equivalents are `/motioncards-retry PACKAGE-ID_rN` to renew an awaiting replacement and `/motioncards-clear PACKAGE-ID_rN` to cancel an awaiting replacement. For an ordinary `failed` group, those commands retain their retry/clear meanings.
- A Telegram notification failure after the confirmation is durably created does not fail publication state. Re-open `/motioncards QID` to recover the pending confirmation.

### Lost acknowledgement recovery

The immutable/durable MotionCards state is the publication-side source of truth; D1 is the control/management projection.

If promotion/state persistence succeeded but the **first** queue acknowledgement was lost, retrying the identical package is recognized as a content duplicate and does not require another content deployment. Before D1 is repaired, the publisher builds a management snapshot from the **current durable state**, revalidates those current records against the currently published MCQs, and sends the active/removed state plus relevant version history to the queue finisher.

D1 applies that reconciliation only when the publication acknowledgement for that exact group/digest is missing. If the acknowledgement already exists, duplicate retry is a management no-op. This prevents an old ZIP from resurrecting a removed card or downgrading a newer replacement. Remove/restore operation acknowledgements use the same durable-current-state reconciliation rule.

## Local preview

`python tools/motioncards.py preview --workspace work/my-batch --port 8767` serves a loopback-only trusted preview host. The index links to host pages with Play/Pause/Restart/Seek and the final Takeaway/Correct answer panel; it does not link directly to handshake-dependent child HTML.

Loopback HTTP is accepted only by the explicit preview compiler mode. Production scene compilation remains HTTPS-origin restricted.

