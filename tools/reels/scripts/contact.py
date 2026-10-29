"""Contact sheet: python3 -I contact.py <out.png> <img> <img> ...   (captioned with the time in the filename)"""
import re
import sys

from PIL import Image, ImageDraw, ImageFont

out, files = sys.argv[1], sys.argv[2:]
COLS = 4 if len(files) > 6 else 3
SCALE = 0.30 if len(files) > 6 else 0.36
ims = [Image.open(f).convert("RGB") for f in files]
w, h = int(ims[0].width * SCALE), int(ims[0].height * SCALE)
rows = (len(ims) + COLS - 1) // COLS
pad = 16
sheet = Image.new("RGB", (COLS * w + (COLS + 1) * pad, rows * (h + 30) + pad), (30, 30, 36))
d = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Bold.otf", 18)
except OSError:
    font = ImageFont.load_default()
for i, (f, im) in enumerate(zip(files, ims)):
    x, y = pad + (i % COLS) * (w + pad), pad + (i // COLS) * (h + 30)
    sheet.paste(im.resize((w, h), Image.LANCZOS), (x, y + 24))
    m = re.search(r"t0*([\d.]+)\.png", f)
    d.text((x, y), f"t = {float(m.group(1)):.2f} s" if m else f, fill=(220, 220, 235), font=font)
sheet.save(out)
print("sheet", out, sheet.size)
