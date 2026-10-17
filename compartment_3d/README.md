# Compartment syndrome, 30 s 3D lesson

One source, two outputs:

- **In the app:** `compartment_3d.html` plays live in the browser (three.js). About 265 KB including the model. No video file, no audio.
- **For YouTube / TikTok / Reels:** the same page is recorded and layered with Manim and FFmpeg. The commands below are written and checked but not run here.

## Files

| File | Role |
|---|---|
| `build_mesh.py` | BodyParts3D OBJ → decimated, packed model (`build/leg.bin`, `build/leg_meta.json`) |
| `compartment_3d.src.html` | The lesson: scene, timeline, captions, quiz |
| `assemble.py` | Inlines the model → `compartment_3d.html` |
| `manim/pressure_curve.py` | Pressure chart, transparent overlay, 11.0–24.4 s |
| `ffmpeg/captions.py` | Captions from the page → ASS (English word-by-word + Arabic) |
| `ffmpeg/compose.sh` | 3D + chart + captions + grade → H.264, 16:9 or 9:16 |
| `record_frames.mjs` | Records the 3D layer (`#clean`) frame by frame |

## Video pipeline (not run here)

```sh
node record_frames.mjs 16x9 frames_16x9
manim -qh -t --fps 30 manim/pressure_curve.py PressureCurve
ffmpeg/compose.sh 16x9 frames_16x9 media/videos/pressure_curve/1080p30/PressureCurve.mov lesson_16x9.mp4
```

## Checks without rendering

```sh
manim --dry_run manim/pressure_curve.py PressureCurve   # runs all 13.4 s of scene logic, writes no video
ffmpeg/compose.sh --check 16x9                         # full filter graph on 2 s of test input, writes nothing
ffmpeg/compose.sh --check 9x16
```

Manim uses `Text` only, so it needs Pango and Cairo but not LaTeX. For the right fonts in the video, put Archivo, IBM Plex Sans Arabic and JetBrains Mono `.ttf` files in `ffmpeg/fonts/` (or set `FONTS_DIR`); otherwise libass and Pango fall back to system fonts.

Anatomy: BodyParts3D, © The Database Center for Life Science, CC BY-SA 2.1 JP.
