"""Merge a slide's part-images into one seamless 16:9 slide image.

Parts are multiply-blended onto one white canvas (white acts as transparent), so
there are no borders or gaps. Wherever a part's drawing is cut off at an inner
edge, that edge is faded so the seam disappears.

Usage:
  python3 merge_slide.py part1.png part2.png ... -o slide.png \
      [--rows 2,1] [--title "Slide title"] [--subtitle "..."] [--size 3840x2160]

--rows says how many parts go in each row, top to bottom (default: automatic).
"""
import argparse
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
NAVY = (22, 33, 72)
GOLD = (200, 140, 0)
WHITE = (255, 255, 255)

AUTO_ROWS = {1: [1], 2: [2], 3: [3], 4: [2, 2], 5: [3, 2], 6: [3, 3], 7: [4, 3], 8: [4, 4]}


def touches(img, side, thresh=235, frac=0.03, strip=4):
    """True when drawn (non-white) content reaches this edge of the image."""
    g = img.convert("L")
    w, h = g.size
    box = {"left": (0, 0, strip, h), "right": (w - strip, 0, w, h),
           "top": (0, 0, w, strip), "bottom": (0, h - strip, w, h)}[side]
    hist = g.crop(box).histogram()
    return sum(hist[:thresh]) / sum(hist) > frac


def whiten(img, level=238):
    """Make near-white background pure white, so it vanishes when blended."""
    r, g, b = img.split()
    darkest = ImageChops.darker(ImageChops.darker(r, g), b)
    mask = darkest.point(lambda v: 255 if v >= level else 0)
    return Image.composite(Image.new("RGB", img.size, WHITE), img, mask)


def fade(img, side, width):
    """Blend `width` px at one edge toward white."""
    mask = Image.new("L", img.size, 255)
    d = ImageDraw.Draw(mask)
    w, h = img.size
    for k in range(width):
        v = int(255 * (k / width) ** 1.5)
        line = {"left": (k, 0, k, h), "right": (w - 1 - k, 0, w - 1 - k, h),
                "top": (0, k, w, k), "bottom": (0, h - 1 - k, w, h - 1 - k)}[side]
        d.line(line, fill=v)
    return Image.composite(img, Image.new("RGB", img.size, WHITE), mask)


def fit_text(d, text, size, max_w):
    f = ImageFont.truetype(FONT, size)
    while d.textlength(text, font=f) > max_w and size > 12:
        size -= 1
        f = ImageFont.truetype(FONT, size)
    return f


def merge(parts, rows, size, title=None, subtitle=None):
    W, H = size
    out = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(out)
    top = 0
    if title:
        ft = fit_text(d, title, int(H * 0.055), W - 120)
        d.text(((W - d.textlength(title, font=ft)) / 2, int(H * 0.025)), title, font=ft, fill=NAVY)
        top = int(H * 0.025) + ft.size + int(H * 0.015)
        if subtitle:
            fs = fit_text(d, subtitle, int(H * 0.025), W - 120)
            d.text(((W - d.textlength(subtitle, font=fs)) / 2, top), subtitle, font=fs, fill=GOLD)
            top += fs.size
        top += int(H * 0.02)

    # Pack parts edge to edge: every part in a row gets the same height and the
    # row spans the full width; then shrink everything to fit and center it.
    parts = [whiten(p.convert("RGB")) for p in parts]
    grid, i = [], 0
    for count in rows:
        grid.append(parts[i:i + count])
        i += count
    heights = [W / sum(p.width / p.height for p in row) for row in grid]
    k = min(1.0, (H - top) / sum(heights))
    y = top + ((H - top) - k * sum(heights)) / 2
    for r, (row, rh) in enumerate(zip(grid, heights)):
        h = round(rh * k)
        widths = [round(p.width / p.height * h) for p in row]
        x = (W - sum(widths)) / 2
        for c, (img, w) in enumerate(zip(row, widths)):
            img = img.resize((w, h), Image.LANCZOS)
            # Inner edges only: an edge on the canvas border may stay cut off.
            inner = {"left": c > 0, "right": c < len(row) - 1, "top": r > 0, "bottom": r < len(grid) - 1}
            for side, is_inner in inner.items():
                if is_inner and touches(img, side):
                    img = fade(img, side, max(20, int(0.04 * (w if side in ("left", "right") else h))))
            box = (round(x), round(y), round(x) + w, round(y) + h)
            out.paste(ImageChops.multiply(out.crop(box), img), box)
            x += w
        y += h
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("parts", nargs="+", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--rows", help="parts per row, e.g. 2,1")
    ap.add_argument("--title")
    ap.add_argument("--subtitle")
    ap.add_argument("--size", default="3840x2160")
    a = ap.parse_args()

    parts = [Image.open(p) for p in a.parts]
    rows = [int(x) for x in a.rows.split(",")] if a.rows else AUTO_ROWS.get(len(parts))
    if rows is None:
        rows = [3] * (len(parts) // 3) + ([len(parts) % 3] if len(parts) % 3 else [])
    if sum(rows) != len(parts):
        ap.error(f"--rows {rows} places {sum(rows)} parts, but {len(parts)} were given")
    w, h = (int(v) for v in a.size.lower().split("x"))
    merge(parts, rows, (w, h), a.title, a.subtitle).save(a.out, optimize=True)
    print(f"saved {a.out} ({w}x{h}, rows={rows})")


if __name__ == "__main__":
    main()
