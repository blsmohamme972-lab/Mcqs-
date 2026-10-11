# PVC → hepatocellular carcinoma (zoom explainer)

`pvc-hcc-explainer.mp4`: 45 s, 1280×720, narrated. The camera zooms in and out across the illustration (question → liver → PVC barrel and fumes → factory → liver → answer).

- The voice-over was made with free Microsoft Edge neural TTS (`edge-tts`, voice `en-US-AndrewNeural`, no API key). See `source/tts.py`. Behind the session proxy it needs the proxy CA bundle and `trust_env`.
- The narration script is in `source/segs.txt`. Caption and segment timing is in `source/timeline.json`.
- `source/render1.js <page.html> <seconds> <out.mp4> <audio.wav>` renders the frames with Playwright and muxes the audio with ffmpeg.
