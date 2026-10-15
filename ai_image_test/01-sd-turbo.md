# 01 – SD-Turbo (local CPU run)

- **Model:** `stabilityai/sd-turbo` (distilled SD 2.1, diffusers `AutoPipelineForText2Image`)
- **License:** Stability AI Community License (non-commercial research use free; commercial use requires registration / revenue cap, see model card)
- **Steps:** 4
- **Guidance scale:** 0.0
- **Seed:** 42 (CPU generator)
- **Native size:** 768x512 (3:2), float32, attention slicing; upscaled to 960x640 with Pillow LANCZOS
- **Hardware:** CPU only, 4 cores, 15 GB RAM (torch 2.14.1+cpu, diffusers 0.41.0)
- **Load time:** ~41 s (from local HF cache after download)
- **Generation time:** ~57 s for 4 steps
- **Peak RAM:** ~7.1 GB (max RSS)

## Quality notes (honest)

- The prompt is ~96 CLIP tokens; everything after "Clean flat vector style…" was **truncated** (77-token limit), so the flat-vector / soft-shading / classroom style cues were ignored. The result is a sketchy ink-and-color comic look rather than clean flat vector.
- **Student / white coat / stethoscope:** yes – a smiling young man in a white coat with a stethoscope around the neck, good likeness to the request.
- **Pointing pose:** partial – one hand points toward a heart, the other holds a red tube-like object; no marker, no clear open-hand explaining gesture. Hands are somewhat malformed.
- **Heart anatomy:** no. Hearts are generic valentine/organ-like red blobs with white squiggles, repeated many times across the board. No four chambers, no recognisable aorta or pulmonary arteries, and **no blue vessels** at all.
- **Whiteboard:** rendered as a blue/teal board with a side panel of small figures.
- **Text garbage:** yes – lots of pseudo-handwriting gibberish ("Gzerg", "GTUK", scribbles) on the board.
- Overall: fast and lightweight on CPU, recognisable subject, but not usable for an anatomically correct educational illustration.
