"""Draw a labelled placeholder for the tension pneumothorax scene until the real illustration exists.

Region boxes are read from manifest.json, so the placeholder always matches the occlusion cards.
Replace media/scene.png with the generated illustration and adjust the region boxes to fit it.
Usage: python3 render_placeholder.py   (needs Pillow)
"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1600, 900
COLORS = {
    "cause": (232, 120, 100),
    "crisis": (120, 160, 230),
    "treat": (90, 190, 140),
}
GROUP = {
    "car": "cause", "beam": "cause", "zipper": "cause",
    "lung": "crisis", "drum": "crisis", "cricket": "crisis", "bubbles": "crisis",
    "wall": "crisis", "heart": "crisis",
    "firefighter": "treat", "plumber": "treat", "chainsaw": "treat",
}


def font(size):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/opentype/inter/Inter-Bold.otf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def main():
    manifest = json.load(open(os.path.join(HERE, "manifest.json")))
    scene = manifest["scenes"][0]
    img = Image.new("RGB", (W, H), (246, 242, 232))
    d = ImageDraw.Draw(img)

    # Rib-cage building: floors are intercostal spaces, rooftop rail is the clavicle.
    bx0, bx1, by0, by1 = 520, 1180, 120, 860
    d.rounded_rectangle([bx0, by0, bx1, by1], 40, outline=(90, 80, 70), width=6)
    for i in range(1, 8):
        y = by0 + i * (by1 - by0) / 8
        d.arc([bx0 - 40, y - 30, bx1 + 40, y + 50], 200, 340, fill=(150, 135, 120), width=5)
        d.text((bx1 + 12, y - 12), f"{i}", fill=(120, 110, 100), font=font(22))
    d.line([bx0 - 30, by0 - 10, bx1 + 30, by0 - 10], fill=(90, 80, 70), width=10)
    d.rectangle([840, by0, 880, by1], fill=(205, 195, 180))

    for r in scene["regions"]:
        x0, y0 = r["x"] * W, r["y"] * H
        x1, y1 = x0 + r["w"] * W, y0 + r["h"] * H
        col = COLORS[GROUP.get(r["id"], "crisis")]
        d.rounded_rectangle([x0, y0, x1, y1], 14, fill=col + (0,), outline=(60, 60, 60), width=3)
        label = r.get("label", r["id"])
        f = font(20)
        words, lines, line = label.split(), [], ""
        for w in words:
            test = (line + " " + w).strip()
            if d.textlength(test, font=f) > (x1 - x0) - 16 and line:
                lines.append(line)
                line = w
            else:
                line = test
        lines.append(line)
        ty = y0 + ((y1 - y0) - 24 * len(lines)) / 2
        for ln in lines:
            d.text(((x0 + x1) / 2, ty), ln, fill=(20, 20, 20), font=f, anchor="ma")
            ty += 24

    d.text((W / 2, 40), "PLACEHOLDER — replace with the generated illustration", fill=(150, 60, 60),
           font=font(28), anchor="ma")
    out = os.path.join(HERE, "media", "scene.png")
    img.save(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
