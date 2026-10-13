"""Merge the four panels into one continuous scene: no borders, headers or gaps.

The panels share a white background, so they are multiply-blended onto one white
canvas (white acts as transparent). Content that ends in a hard cut at an inner
edge (the blood vessel in panel 2) is faded in so the seam disappears.
Outputs:
  carbohydrates_seamless.png           2x2 scene
  carbohydrates_seamless_vertical.png  one column, for phone scrolling
"""
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

from merge import FONT, HERE, NAVY, PANELS, PH, PW, SUBTITLE, TITLE

GOLD_TEXT = (200, 140, 0)


def panel(i):
    return Image.open(HERE / "panels" / PANELS[i][0]).convert("RGB").resize((PW, PH))


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
        d.text(((canvas.width - d.textlength(text, font=f)) / 2, y), text, font=f, fill=fill)


def grid():
    top = 230
    W, H = 2 * PW, top + 2 * PH
    out = Image.new("RGB", (W, H), (255, 255, 255))
    title(out, 50, 96, 44)
    # Panel 2's vessel and panel 1's key are cut at inner edges: fade them in/out.
    stamp(out, fade_edge(panel(0), "bottom", 90), (0, top))
    stamp(out, fade_edge(panel(1), "left"), (PW, top))
    stamp(out, panel(2), (0, top + PH))
    stamp(out, panel(3), (PW, top + PH))
    return out


def vertical(overlap=70):
    top = 190
    W, H = PW, top + 4 * PH - 3 * overlap
    out = Image.new("RGB", (W, H), (255, 255, 255))
    title(out, 40, 64, 30)
    for i in range(4):
        img = fade_edge(panel(i), "bottom", 90) if i == 0 else panel(i)
        stamp(out, img, (0, top + i * (PH - overlap)))
    return out


if __name__ == "__main__":
    grid().save(HERE / "carbohydrates_seamless.png", optimize=True)
    vertical().save(HERE / "carbohydrates_seamless_vertical.png", optimize=True)
    print("saved")
