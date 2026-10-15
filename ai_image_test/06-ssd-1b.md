# 06 — segmind/SSD-1B

- **Model:** [`segmind/SSD-1B`](https://huggingface.co/segmind/SSD-1B) (distilled SDXL, ~1.3B UNet), base model, **no LCM-LoRA**
- **License:** Apache-2.0
- **Pipeline:** diffusers 0.41.0 `StableDiffusionXLPipeline`, torch 2.14.1+cpu, float32, attention slicing on
- **Steps:** 20 (default scheduler)
- **Guidance:** 7.0
- **Seed:** 42 (`torch.Generator("cpu")`)
- **Size:** generated natively at 960x640, so no resize was needed (SSD-1B handles SDXL-style non-square sizes)
- **Negative prompt:** `ugly, blurry, poor quality, text, watermark`
- **Prompt:** the one in `PROMPT.md`, unchanged
- **Hardware:** CPU only, 4 cores, 15 GB RAM
- **Generation time:** 367 s (~18 s/step) for the denoising run, plus 69 s to load the model from cache (the first download took extra)
- **Peak RAM (process RSS):** 11.85 GB

## Quality notes

- **Style:** a clean, bright cartoon / comic illustration with soft shading on a near-white background. The style is good, but there's almost no "classroom" in the background.
- **Student:** cheerful, smiling, glasses, white coat. The open-hand gesture toward the board is there. There's **no marker** and no real pointing pose: the hand is open and raised.
- **Stethoscope:** only partly there. There's a small stethoscope-like chest piece on the coat and a cord, but it is **not around the neck**. The red tie took over the neckline instead.
- **Whiteboard:** drawn as a monitor/screen on a stand, not a whiteboard.
- **Heart:** a fairly anatomical heart with a red aorta-like vessel on top and red/blue colouring (blue for the right side/veins). It looks good at a glance. There are **no visible four chambers**, and the pulmonary arteries can't be identified clearly. A red line runs down from the heart like a stem.
- **Extras / artifacts:** a stray floating red "love heart" with branching red lines between the student and the board. There's faint sketchy pseudo-text and scribbles on the screen (small, not glaring garbage text). There's also an odd microphone/clamp object at the bottom of the stand.
- **Overall:** good, friendly look that's close to usable as a hero image. The anatomy isn't precise enough to teach from, and several prompt details are missing or substituted (whiteboard, marker, stethoscope around the neck).
