# Visual style guide

One look across the app, the reels and the mnemonic images: **dark, glossy, neon, cute.**
Attractive enough that opening the app feels like a treat, never at the cost of accuracy.

## Palette (same tokens as `ui/Theme.kt` and `tools/render_reel.py`)

| Token | Hex | Use |
|---|---|---|
| Ink | `#0B0B12` | Backgrounds |
| Panel / Panel2 | `#15151F` / `#1E1E2B` | Cards, sheets |
| Pink | `#FF3D7F` | Brand, the asked region, progress |
| Violet | `#8B5CF6` | Brand gradient end |
| Cyan | `#22D3EE` | Revealed answers, "Easy" |
| Text | `#F2F2F7` / `#A1A1B5` | Primary / secondary text |

Brand gradient: Pink → Violet. Cool gradient: Violet → Cyan.

## Mnemonic images (prompt style block)

Paste this at the top of every image prompt (see `prompts/`):

```
Style: cute chibi characters with big expressive eyes, glossy soft-3D vector look,
rounded shapes, vibrant neon accents (hot pink #FF3D7F, violet #8B5CF6, cyan #22D3EE)
on a deep dark navy background, soft rim lighting and subtle glow, clean composition,
playful and charming, family-friendly. Medical structures stay anatomically sensible.
NO text, NO letters, NO numbers, NO labels anywhere.
```

Rules:
- **Cute, not crude.** Charm comes from expressions, poses and colour — keep it family-friendly.
- **Same character = same look** in every scene (the lung is always the pink balloon, the heart
  always the red heart, the hero always the same firefighter). Generate recurring characters once,
  reuse them.
- **6–12 story elements** per scene, each with breathing room so its occlusion box doesn't cover
  its neighbours.
- **Never let the image carry a fact the book doesn't** — the mnemonic points at the book's text.

## Reels

- Vertical 9:16 (720×1280 or 1080×1920), 15–60 s.
- Built with `tools/render_reel.py`: dark gradient background, gradient title, camera glides to
  each region, caption = card question (small) + answer (large), pink progress bar.
- Narration (Breeze TTS 2 / Fish S2 Pro) is muxed with `--audio`.
