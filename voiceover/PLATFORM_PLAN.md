# Platform changes for voice-over: what is done, what is left

## Done (one owner-reviewed PR, three commits)

### 1. Card delivery is free and unlimited (Golden rules 4–6)
- **What changed:**
  - `motioncards-worker/_headers` carries the CSP sandbox, CORS, cache and security headers.
  - `run_worker_first` is removed from `wrangler.jsonc`.
- **Effect:** card and index requests are served by Cloudflare's static asset layer without running Worker code. They no longer count toward the Workers Free plan's 100,000 requests/day, which the whole account shares, so they can't hit 429 errors.
- **Proof:**
  - The real Wrangler runtime test (`tools/ui/motioncards_worker_runtime.py`) passes, including the sandbox handshake in a browser.
  - The headers are byte-identical to before.
  - `worker.test.mjs` checks that `_headers` matches `worker.mjs` and that `run_worker_first` stays off.
- **Deploy safety:** the publish workflow copies `_headers` into `dist/` and refuses to deploy unless the CSP sandbox is in it.

### 2. Voice in the package (Golden rules 2, 3)
- **Packaging:**
  - `motioncards.py package` reads `work/<batch>/voice/<QID>.opus` and `.track.json` (made by `voiceover.py make`).
  - It packages them as `voice/<QID>.opus` with a manifest `voice` block.
  - It **refuses a card without voice**; `--no-voice` exists only for re-packaging old silent cards.
- **Validator:** exact path, Ogg Opus magic, at most 64 KB, SHA-256, and the real stream length (read from the Ogg granule) must fit the card and match `track_ms`. Cues must be ordered and inside the card; no other audio is allowed. The entry is rebuilt byte for byte, voice included.
- **Compiler** (v2 cards only; v1 output is frozen and unchanged): embeds the track as base64, plus a small script that hands the exact bytes to the app over the card's verified MessageChannel right after `ready`. The card's CSP stays `media-src 'none'`.
- **Publisher index:** carries `voice {mime, bytes, sha256, track_ms}`, so the app can verify the bytes it receives.
- **Tests:** `tools/tests/test_motioncards_voice.py` covers packaging, 8 tampering cases, the index, and a real-browser hand-over (exact bytes after `ready`).

### 3. The app plays the voice (Golden rule 7)
- `app/modules/motioncards-voice.js` (the audio-led clock) is loaded before the player.
- **`motioncards-player.js`:**
  - Accepts the `voice` message only if mime, size and SHA-256 match the index exactly.
  - Plays on the student's own Play tap.
  - Uses the voice as the master clock while it plays.
  - Pause, seek, restart, close and retry all move or release the voice.
- **Mute button:** shown only when a verified voice is present; the choice is remembered.
- **App flow test** (`tools/ui/flows/11_motioncards.py`, `voice_case`):
  - The verified voice plays and the picture follows it within 150 ms.
  - Pause and seek move the voice, and mute persists.
  - A voice whose bytes don't match the index is never played, and the card still plays.

### 4. Cards and voice saved on the device
- **What it does:** when a chapter is saved for offline, its MotionCards (each with its voice inside) are saved in the app's Cache Storage (`kafu-motioncards-v1`). A card is also saved the first time it plays.
- **Integrity:** a stored card is used only if its bytes match the index `entry_sha256`.
- **Security:** it plays from a `blob:` URL in the same `sandbox="allow-scripts"` iframe, with the card's CSP added as a `<meta>` tag. The card still gets an opaque origin, no storage and no network.
- **Network use:** after the first download, opening a card makes no card request; offline, the chapter's saved index copy keeps the button.
- **Cleanup:** deleting the chapter removes its cards, and a newer revision replaces older copies when the chapter is saved again.
- **Fallback:** without Cache Storage, the card loads from the network as before.

## Left to do
- **Shards for 300+ books (Golden rule 6):** the free plan allows 20,000 files per Worker version, about 75 books at one file per card. Before the published card count nears 20,000, publish by book to `kafu-motioncards-1 … N`. The free plan allows 100 Workers, and each one is assets-only, so each stays free and unlimited. The index records each card's URL, so the app needs no change.
- **iPhones older than iOS 18.4** (no Ogg Opus): today the card plays silently there (no error, and the mute button stays hidden). Optional upgrade: lazy-load a small WASM Opus decoder on those phones only; check its licence and size first.
- **Deploy:** after this PR is merged, the app deploy workflow ships the player, and the next MotionCards publish ships `_headers` with the new Worker config. Voiced ZIPs then work end to end.
