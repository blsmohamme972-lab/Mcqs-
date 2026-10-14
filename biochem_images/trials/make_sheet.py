"""Contact sheet of all trials: image + settings, time and peak RAM under each.

Usage: python3 make_sheet.py [out.png]   (run from anywhere; reads out/NN/result.json)
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
CELL, COLS, PAD, CAP = 640, 5, 24, 120


def caption(r):
    c = r["config"]
    model = "Turbo" if c["turbo"] else f"Full CFG {c['cfg']:g} x{c['steps']}"
    line1 = f"#{r['id']}  {model}  {c['quant']}  {c['W']}x{c['H']}"
    extras = {"P2": "no text", "P3": "text-rich"}.get(c["prompt"], "")
    if not c["offload"]:
        extras = (extras + " no-offload").strip()
    mins = round(r["run_seconds"] / 60)
    line2 = f"{mins} min   RAM {r['peak_rss_mb'] / 1000:.1f} GB   {extras}".strip()
    return line1, line2


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "contact_sheet.png"
    results = [json.loads(p.read_text()) for p in sorted((HERE / "out").glob("*/result.json"))]
    rows = (len(results) + COLS - 1) // COLS
    W = COLS * (CELL + PAD) + PAD
    H = 110 + rows * (CELL + CAP + PAD) + PAD
    sheet = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    d.text((PAD, 24), "Cavernous sinus thrombosis: same prompt, 10 settings (Qwen-Image 2.1, CPU)",
           font=ImageFont.truetype(BOLD, 40), fill=(22, 33, 72))
    d.text((PAD, 72), "Turbo = 8-step LoRA, CFG 1.  Full = no LoRA, CFG 4 + negative prompt.  Time is the image run only.",
           font=ImageFont.truetype(REG, 24), fill=(90, 90, 90))
    for i, r in enumerate(results):
        x = PAD + (i % COLS) * (CELL + PAD)
        y = 110 + (i // COLS) * (CELL + CAP + PAD)
        img = Image.open(HERE / "out" / r["id"] / "image.png").convert("RGB")
        img.thumbnail((CELL, CELL))
        box = Image.new("RGB", (CELL, CELL), (255, 255, 255))
        box.paste(img, ((CELL - img.width) // 2, (CELL - img.height) // 2))
        sheet.paste(box, (x, y))
        d.rectangle((x, y, x + CELL - 1, y + CELL - 1), outline=(22, 33, 72), width=2)
        l1, l2 = caption(r)
        d.text((x, y + CELL + 10), l1, font=ImageFont.truetype(BOLD, 28), fill=(22, 33, 72))
        d.text((x, y + CELL + 52), l2, font=ImageFont.truetype(REG, 25), fill=(70, 70, 70))
    sheet.save(out, optimize=True)
    print("saved", out, sheet.size)


if __name__ == "__main__":
    main()
