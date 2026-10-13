"""Merge the four carbohydrate mnemonic panels into one study poster.

Panels are pasted untouched (no AI re-generation), so every label stays exactly as drawn.
Outputs:
  carbohydrates_poster.png           2x2 grid, read 1 -> 2 -> 3 -> 4
  carbohydrates_poster_vertical.png  single column, for phone scrolling
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

NAVY = (22, 33, 72)
GOLD = (245, 180, 0)
RED = (205, 40, 45)
BG = (255, 255, 255)
CARD = (250, 247, 240)

TITLE = "Carbohydrates: Glucose, the King of Fuels"
SUBTITLE = "Why glucose matters  →  where it comes from  →  what it builds  →  what goes wrong"

PANELS = [
    ("1_glucose_king.png", "Glucose = major fuel", "Universal fetal fuel • mammals (except ruminants) • precursor of all other carbs"),
    ("2_sources.png", "Where glucose comes from", "Dietary carbohydrate absorbed • liver converts other sugars to glucose"),
    ("3_precursor.png", "What glucose builds", "Glycogen (storage) • ribose / deoxyribose (nucleic acids) • galactose (lactose, glycoconjugates)"),
    ("4_diseases.png", "When it goes wrong", "Diabetes • galactosemia • fructose & lactose intolerance • glycogen storage diseases"),
]

PW, PH = 1536, 1024          # panel size
PAD = 48                     # outer / gap padding
HEAD = 150                   # per-panel header height
TITLE_H = 230


def font(size, bold=True):
    return ImageFont.truetype(FONT if bold else FONT_REG, size)


def centered(draw, cx, y, text, fnt, fill):
    w = draw.textlength(text, font=fnt)
    draw.text((cx - w / 2, y), text, font=fnt, fill=fill)


def card(idx):
    """One panel with a numbered header, as its own image."""
    name, heading, note = PANELS[idx]
    img = Image.new("RGB", (PW, PH + HEAD), CARD)
    d = ImageDraw.Draw(img)
    # number badge
    r = 48
    cx, cy = 30 + r, HEAD // 2
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=GOLD, outline=NAVY, width=5)
    centered(d, cx, cy - 34, str(idx + 1), font(58), NAVY)
    d.text((cx + r + 28, 22), heading, font=font(54), fill=NAVY)
    size = 30
    while d.textlength(note, font=font(size, bold=False)) > PW - (cx + r + 60) and size > 18:
        size -= 1
    d.text((cx + r + 30, 92), note, font=font(size, bold=False), fill=(70, 70, 70))
    img.paste(Image.open(HERE / "panels" / name).convert("RGB").resize((PW, PH)), (0, HEAD))
    d.rectangle((0, 0, PW - 1, PH + HEAD - 1), outline=NAVY, width=6)
    return img


def title_block(width):
    img = Image.new("RGB", (width, TITLE_H), NAVY)
    d = ImageDraw.Draw(img)
    centered(d, width / 2, 40, TITLE, font(92 if width > 2000 else 64), (255, 255, 255))
    centered(d, width / 2, 160 if width > 2000 else 140, SUBTITLE, font(40 if width > 2000 else 28, bold=False), GOLD)
    return img


def arrow(d, x1, y1, x2, y2, w=14):
    d.line((x1, y1, x2, y2), fill=RED, width=w)
    # arrow head pointing toward (x2, y2)
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    L = 40
    p1 = (x2 - L * math.cos(a - 0.5), y2 - L * math.sin(a - 0.5))
    p2 = (x2 - L * math.cos(a + 0.5), y2 - L * math.sin(a + 0.5))
    d.polygon([(x2, y2), p1, p2], fill=RED)


def grid():
    cw, ch = PW, PH + HEAD
    W = 2 * cw + 3 * PAD
    H = TITLE_H + 2 * ch + 3 * PAD
    out = Image.new("RGB", (W, H), BG)
    out.paste(title_block(W), (0, 0))
    pos = [(PAD, TITLE_H + PAD), (2 * PAD + cw, TITLE_H + PAD),
           (PAD, TITLE_H + 2 * PAD + ch), (2 * PAD + cw, TITLE_H + 2 * PAD + ch)]
    for i, p in enumerate(pos):
        out.paste(card(i), p)
    d = ImageDraw.Draw(out)
    # 1 -> 2 and 3 -> 4 across the vertical gap, 2 -> 3 across the horizontal gap
    ymid1 = pos[0][1] + HEAD // 2
    ymid2 = pos[2][1] + HEAD // 2
    arrow(d, PAD + cw - 4, ymid1, 2 * PAD + cw + 6, ymid1)
    arrow(d, PAD + cw - 4, ymid2, 2 * PAD + cw + 6, ymid2)
    return out


def vertical():
    cw, ch = PW, PH + HEAD
    W = cw + 2 * PAD
    H = TITLE_H + 4 * ch + 5 * PAD
    out = Image.new("RGB", (W, H), BG)
    out.paste(title_block(W), (0, 0))
    d = ImageDraw.Draw(out)
    for i in range(4):
        y = TITLE_H + PAD + i * (ch + PAD)
        out.paste(card(i), (PAD, y))
        if i:
            arrow(d, W // 2, y - PAD - 2, W // 2, y + 6)
    return out


if __name__ == "__main__":
    grid().save(HERE / "carbohydrates_poster.png", optimize=True)
    vertical().save(HERE / "carbohydrates_poster_vertical.png", optimize=True)
    print("saved")
