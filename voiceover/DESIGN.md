# Voice-over design and evidence

All measurements were taken in this repo's Claude Code container on 8 Oct 2026 unless stated otherwise.

## 1. Voice engine: Kokoro-82M (Golden rule 1)

| Option | Quality | Cost | Verdict |
|---|---|---|---|
| **Kokoro-82M v1.0** via `kokoro-onnx` 0.6.1 | Near-natural; ranked among the best open models on the public TTS Arena despite its small size | Free. Weights are **Apache-2.0** (model card: "deployed anywhere from production environments to personal projects") | **Chosen** |
| Piper | Good, more robotic | Free; the maintained engine (piper1-gpl) is GPL-3.0, and each voice has its own licence | Backup |
| Cloud TTS (Google, Azure, ElevenLabs, OpenAI) | Very good | Paid per character, needs keys and an account | Breaks rules 3 and 4 |
| Browser `speechSynthesis` on the student's phone | Varies by phone, often robotic; can't be checked or synced | Free | Breaks rules 1 and 7 |

- **Voice:** `af_heart`, rated **A** in Kokoro's VOICES.md (the best grade; `af_bella` is A-). A British alternative is `bf_emma` (B-), selected with `--voice bf_emma --lang en-gb`. One voice per book keeps it consistent.
- **Model:** fp32 `kokoro-v1.0.onnx`, pinned by SHA-256 `7d5df8ec…`; voices file `voices-v1.0.bin`, `bca610b8…`. The int8 model was **slower** on this CPU (12.6 s vs 3.5 s for 9 s of speech), so fp32 is used.
- **Speed:** 9 s of speech is made in about 3.5 s. For an 8-card chapter on a 4-vCPU container: synth about 40 s, check about 1 min (more the first time a line needs the second recogniser), review videos about 2.5 min.
- The phonemiser (the `phonemizer` package and espeak-ng, both GPL-3.0) runs only at build time on Claude's machine. It is not shipped, and the audio it helps make is ours to use.
- **Checked again on 8 Oct 2026:** no newer free, commercially licensed model beats Kokoro + `af_heart`. It is the top open-weights row on TTS Arena V2. The better-scoring open models have non-commercial or restricted licences.

## 2. Codec and bitrate (Golden rules 1, 5)

The same 9.1 s sentence, encoded with libopus (mono, 24 kHz, VBR, 60 ms frames):

| Bitrate | Size | Speech recogniser result |
|---|---|---|
| 12 kbps | 13.5 KB | Every word correct |
| **16 kbps** | **18.8 KB** | Every word correct |
| 20 kbps | 23.0 KB | Every word correct |
| 24 kbps | 27.5 KB | Every word correct |

- **Chosen: Opus 16 kbps, `-application voip`.** That is about 2 KB per second of speech; a real 8 s card averages 12.6 KB because pauses cost almost nothing. 12 kbps is still fully intelligible but starts to sound slightly thin; 16 kbps is the safe point for quality per byte.
- **Opus vs AAC/MP3:** at these rates Opus is clearly better for speech. AAC-LC needs about 32 kbps and MP3 about 48 kbps for similar quality, so files would be 2–3× larger.
- **Container: Ogg.** Chrome, Android WebView, Firefox and desktop Telegram all play it. **iPhone/Safari has played Ogg Opus since Safari 18.4 (March 2025).** For older iPhones, see PLATFORM_PLAN.md (WASM decoder fallback).
- **Loudness** is normalised to −16 LUFS (−1.5 dBTP) so every card plays at the same volume.
- **Encoding is bit-exact:** the same input always gives the same bytes (checked twice). The SHA-256 in the manifest therefore stays stable, and rebuilds are reproducible.

## 3. Sync (Golden rule 7)

Sync happens at three levels, each checked:

1. **Script level:** the beats are the card's numbered captions and their `show` windows (0–2.7 s, 2.7–5 s, 5–8 s for an 8 s card). `draft` gives each beat a word budget (6, 5 and 6 words on an 8 s card). `synth` speeds a line up by at most 1.2× to fit, and otherwise **refuses** it and says how many words to cut. On chapter 10 it caught 3 lines that would have overrun.
2. **Audio level:** each line is made as its own clip, its leading silence is trimmed, and it is placed so the first word starts 250 ms (beat 1) or 120 ms (later beats) after its beat begins. That is when the caption has appeared and the animation step is under way. `check` measures every start **from the waveform**: chapter 10 is **0–40 ms** from target on all 24 beats (limit 80 ms; broadcast standards accept about 45 ms early to 125 ms late).
3. **Playback level:** in the app, the voice is the **master clock** while it plays (`app/modules/motioncards-voice.js`). Each frame the animation time is taken from the audio position, smoothed between the browser's coarse audio-clock updates. If the audio stalls on a slow phone, the animation waits instead of running ahead. Seek, pause and restart move both together. If something outside the app pauses the voice (a call, an unplugged headset, the lock screen), the picture pauses with it, and only the app's Play starts the voice again. If voice and picture drift more than 1 s apart (a late start or a stall), the voice is moved to the picture. Real Chromium test: drift **under 60 ms** through play, seek, pause, resume and restart, plus an outside pause and a fast play–pause–play.

Each beat's text and start time is also stored as a `cue` (`.track.json`). That makes subtitles or word highlighting possible later at no extra cost.

## 4. Pronunciation quality

`check` listens to every track with a free speech recogniser (faster-whisper `base.en`, MIT) and compares what it hears with what was meant to be said. It also measures timing.

- **Each line is heard on its own** (its own slice of audio, at temperature 0). Run over the whole track, the recogniser invented sentences in the silence after the last line, and the old check passed them.
- **Every word of 5+ letters must be heard clearly.** A whole-line score alone passed "ketosidosis" (0.87) and "venous" said as "Venice".
- **A second opinion before failing.** When only a long word is in doubt, the larger `small.en` must hear the same error before the card fails. `base.en` alone falsely flagged correctly spoken "vasoconstriction", "sympathectomy" and "cholinergic".
- **Spelling differences are ignored:** UK/US spellings, number words and y/i.
- **The track must be silent between lines** (below −50 dB of its peak). On chapter 10 it is −91 dB.

A run over 59 MRCS words found real errors, now fixed in `lexicon.json` with exact IPA:

- ketoacidosis was said as "keto-sidosis" (the phonemiser dropped the "a"); ketones as "KET-ones"
- bilirubin was "BYE-lurr-oo-bin"; caecum had a hard K; cholecystectomy lost a syllable
- hepatomegaly, jejunum, lipolysis and creatinine were also fixed
- venous was "VEN-us" (heard as "Venice"), and cholinergic started with "kah" (found on chapter 9)

Abbreviations are expanded before speaking (`INR` becomes "I N R", `NH₃` becomes "ammonia", `→` becomes a pause). New errors are caught by the check, never by a student.

## 5. Delivery: the voice lives inside the card (Golden rules 2, 4, 5)

- **Packaging:** in the MotionCards ZIP, `voice/<QID>.opus` sits next to `entries/`, `scenes/` and `source/`. The manifest records its path, bytes, SHA-256, duration and cues. Same bot, same validation, same `replace` confirmation.
- **Publishing:** the compiler embeds the Opus bytes, base64-encoded, in the card's own HTML entry. The deterministic rebuild in the validator still works, because the voice file is part of the package input.
- **In the app:** the card (sandboxed iframe, `media-src 'none'` unchanged) hands the bytes to the host over the existing MessageChannel. The host checks size and SHA-256, makes a Blob URL, and plays it on the student's own Play tap. That tap is the gesture iOS and Telegram need before sound can start.
- **Why embed rather than ship a separate file?** It costs **0 extra requests and 0 extra files** on Cloudflare (both are capped on the free plan, see §6). Offline downloads also carry the voice automatically. Embedding costs nothing on the wire: base64 adds 33%, but compression removes it (18,828 B Opus → 25,104 B base64 → 18,927 B gzipped).

## 6. Free-plan maths

| Item | Per card | 300 books × ≈ 500 MCQs (≈ 150,000 cards) |
|---|---|---|
| Voice size (Opus 16 kbps, about 1.6 KB per second of card) | ≈ 12.6 KB for 8 s, ≈ 18 KB for 12 s, never above 20 KB | ≈ 2–2.8 GB, no storage charge for Worker static assets |
| Extra Cloudflare requests | **0** | **0** |
| Extra files | **0** | **0** |
| Extra download per card view | ≈ 13 KB (compressed) | free bandwidth |
| Generation cost | ≈ 5 s CPU on Claude's machine | free |
| Model or API fees | 0 | 0 |

### 300 books: two existing limits to fix first

These limits exist with or without voice. Rules 5 and 6 cannot be met until they are fixed:

1. **Card views running Worker code: fixed.** `run_worker_first` was dropped and the headers moved to a static `_headers` file, so card views are free and unlimited. Requests that match no file, such as a book index that does not exist yet, still run the Worker script and count toward the account's **100,000 requests a day**. Making the MotionCards Worker assets-only would remove that too.
2. **20,000 files per Worker version on the free plan** (paid plans got 100,000 in Sept 2025; free stayed at 20,000). The publisher keeps up to 3 files per card (the active entry plus 2 old versions), so one Worker holds about 6,600–20,000 cards, roughly 13–40 books of 500. **Fix:** shard by book across a few MotionCards Workers (`kafu-motioncards-1…N`; the free plan allows up to 100). This needs platform work: today the app, bot and publisher all hard-code one MotionCards origin. Keep only one old version per card, and count files before each publish.

## 7. Ideas included, and ideas for later

Included:
- One command per step; refuses to continue when the script doesn't fit.
- Listen-back pronunciation check, waveform sync check, review MP4s for the owner.
- Pinned, checksummed model; bit-exact audio; cues stored for subtitles.
- Remembered mute; plays only on the student's own tap.

Later:
- **Subtitles or word highlighting** from the stored cues (accessibility, silent study in libraries).
- **Speed control** (0.9× / 1.1×): the audio-led clock keeps sync automatically.
- **Arabic narration:** Kokoro has no Arabic voice. Re-evaluate free Arabic models (Piper `ar_JO`, or newer ones) when needed; the pipeline only needs a new `speak()`.
- **Fine-tuned medical lexicon** shared across all books; it grows as `check` finds words.
