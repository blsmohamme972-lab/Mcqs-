"""Merge all panels into one continuous scene: no borders, headers or gaps.

The panels share a white background, so they are multiply-blended onto one white
canvas (white acts as transparent). Content that ends in a hard cut at an inner
edge (panel 2's blood vessel, panel 6's intestine) is faded in so the seam disappears.
Outputs:
  carbohydrates_seamless.png           two-column scene, read left to right, top to bottom
  carbohydrates_seamless_vertical.png  one column, for phone scrolling
"""
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

from merge import FONT, HERE, NAVY, PH, PW

GOLD_TEXT = (200, 140, 0)
TITLE = "Carbohydrates: Glucose & the Monosaccharides"
SUBTITLE = ("Why glucose matters  \u2192  sources  \u2192  what it builds  \u2192  diseases"
            "  \u2192  monosaccharides  \u2192  sugar alcohols")

# (file, edges whose content is cut off at an inner seam and should fade)
PANELS = [
    ("1_glucose_king.png", {"bottom": 90}),
    ("2_sources.png", {"left": 45}),
    ("3_precursor.png", {}),
    ("4_diseases.png", {}),
    ("5_monosaccharides.png", {}),
    ("6_polyols.png", {"left": 45}),
]


def panel(i, fades=True):
    img = Image.open(HERE / "panels" / PANELS[i][0]).convert("RGB").resize((PW, PH))
    if fades:
        for side, width in PANELS[i][1].items():
            img = fade_edge(img, side, width)
    return img


def fade_edge(img, side, width=45):
    """Blend `width` px at one edge toward white so cut-off content fades in."""
    img = img.copy()
    white = Image.new("RGB", img.size, (255, 255, 255))
    mask = Image.new("L", img.size, 255)
    d = ImageDraw.Draw(mask)
    for k in range(width):
        v = int(255 * (k / width) ** 1.5)
        if side == "left":
            d.line((k, 0, k, img.height), fill=v)
        elif side == "right":
            d.line((img.width - 1 - k, 0, img.width - 1 - k, img.height), fill=v)
        elif side == "bottom":
            d.line((0, img.height - 1 - k, img.width, img.height - 1 - k), fill=v)
    return Image.composite(img, white, mask)


def stamp(canvas, img, xy):
    """Multiply-blend img onto canvas at xy (white = transparent)."""
    x, y = xy
    box = (x, y, x + img.width, y + img.height)
    canvas.paste(ImageChops.multiply(canvas.crop(box), img), box)


def title(canvas, top, size_t, size_s):
    d = ImageDraw.Draw(canvas)
    for text, size, fill, y in ((TITLE, size_t, NAVY, top), (SUBTITLE, size_s, GOLD_TEXT, top + size_t + 24)):
        f = ImageFont.truetype(FONT, size)
        while d.textlength(text, font=f) > canvas.width - 60:
            size -= 1
            f = ImageFont.truetype(FONT, size)
        d.text(((canvas.width - d.textlength(text, font=f)) / 2, y), text, font=f, fill=fill)


def grid():
    top = 230
    rows = (len(PANELS) + 1) // 2
    W, H = 2 * PW, top + rows * PH
    out = Image.new("RGB", (W, H), (255, 255, 255))
    title(out, 50, 96, 40)
    for i in range(len(PANELS)):
        stamp(out, panel(i), ((i % 2) * PW, top + (i // 2) * PH))
    return out


def vertical(overlap=70):
    top = 190
    n = len(PANELS)
    W, H = PW, top + n * PH - (n - 1) * overlap
    out = Image.new("RGB", (W, H), (255, 255, 255))
    title(out, 40, 60, 19)
    for i in range(n):
        # In one column, left/right edges are canvas edges, so only keep bottom fades.
        img = panel(i, fades=False)
        if "bottom" in PANELS[i][1]:
            img = fade_edge(img, "bottom", PANELS[i][1]["bottom"])
        stamp(out, img, (0, top + i * (PH - overlap)))
    return out


if __name__ == "__main__":
    grid().save(HERE / "carbohydrates_seamless.png", optimize=True)
    vertical().save(HERE / "carbohydrates_seamless_vertical.png", optimize=True)
    print("saved")
