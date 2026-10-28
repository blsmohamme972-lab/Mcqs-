"""Render a vertical (9:16) reel for a scene: the camera glides over each region in story order
while its fact appears as a caption. Code moves the image; no hand animation per topic.

Captions come from the occlusion cards (`back`) of that scene, so the reel and the cards always
teach the same facts. Pass --audio to mux a narration track (e.g. from Breeze TTS 2 / Fish S2 Pro).

Usage:
  python3 tools/render_reel.py content/<package-id> <scene-id> [--audio narration.wav]
Writes media/<scene>_reel.mp4 inside the package and sets the scene's "video" in manifest.json.
Needs Pillow and ffmpeg.
"""
import argparse
import json
import math
import os
import subprocess

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 720, 1280, 30
INTRO, PER_REGION, OUTRO = 2.0, 1.6, 1.8
INK = (11, 11, 18)
PINK = (255, 61, 127)
VIOLET = (139, 92, 246)
WHITE = (242, 242, 247)
MUTED = (161, 161, 181)
FONT_DIR = "/usr/share/fonts/opentype/inter"


def font(size, weight="Bold"):
    path = f"{FONT_DIR}/Inter-{weight}.otf"
    if not os.path.exists(path):
        path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    return ImageFont.truetype(path, size)


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def wrap(draw, text, fnt, width):
    lines, line = [], ""
    for word in text.split():
        test = (line + " " + word).strip()
        if draw.textlength(test, font=fnt) > width and line:
            lines.append(line)
            line = word
        else:
            line = test
    if line:
        lines.append(line)
    return lines


def gradient_text(img, xy, text, fnt, anchor="ma"):
    """Pink→violet gradient text."""
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).text(xy, text, font=fnt, fill=255, anchor=anchor)
    box = mask.getbbox()
    if not box:
        return
    grad = Image.new("RGB", (box[2] - box[0], 1))
    for x in range(grad.width):
        t = x / max(1, grad.width - 1)
        grad.putpixel((x, 0), tuple(int(lerp(PINK[i], VIOLET[i], t)) for i in range(3)))
    grad = grad.resize((box[2] - box[0], box[3] - box[1]))
    img.paste(grad, box[:2], mask.crop(box))


def background():
    bg = Image.new("RGB", (W, H), INK)
    glow = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(glow)
    d.ellipse([-200, -100, 500, 600], fill=(70, 20, 60))
    d.ellipse([300, 800, 1000, 1500], fill=(40, 25, 90))
    return Image.blend(bg, glow.filter(ImageFilter.GaussianBlur(160)), 0.9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("package")
    ap.add_argument("scene")
    ap.add_argument("--audio")
    args = ap.parse_args()

    mpath = os.path.join(args.package, "manifest.json")
    manifest = json.load(open(mpath, encoding="utf-8"))
    scene = next(s for s in manifest["scenes"] if s["id"] == args.scene)
    regions = {r["id"]: r for r in scene["regions"]}
    beats = [(regions[c["region"]], c["back"], c["front"]) for c in manifest["cards"]
             if c["type"] == "occlusion" and c.get("scene") == scene["id"] and c.get("region") in regions]

    src = Image.open(os.path.join(args.package, scene["image"])).convert("RGB")
    sw, sh = src.size
    bg = background()
    view_w, view_h = W - 48, int((W - 48) * 0.75)   # viewport for the image, 4:3
    view_y = 300

    # Camera keyframes (centre x, centre y, zoom) in source pixels: overview, then each region.
    overview = (sw / 2, sh / 2, max(sw / view_w, sh / view_h))
    cams = [overview]
    for r, _, _ in beats:
        cx, cy = (r["x"] + r["w"] / 2) * sw, (r["y"] + r["h"] / 2) * sh
        span = max(r["w"] * sw / view_w, r["h"] * sh / view_h) * 1.6
        cams.append((cx, cy, max(span, overview[2] * 0.28)))
    cams.append(overview)

    total = INTRO + PER_REGION * len(beats) + OUTRO
    frames = int(total * FPS)
    title_f, cap_f, small_f = font(52, "ExtraBold"), font(40, "Bold"), font(26, "SemiBold")

    out = os.path.join(args.package, "media", f"{scene['id']}_reel.mp4")
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-"]
    if args.audio:
        cmd += ["-i", args.audio, "-shortest", "-c:a", "aac", "-b:a", "128k"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "24", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    for i in range(frames):
        t = i / FPS
        # Which camera segment are we in?
        if t < INTRO:
            a, b, k, beat = 0, 0, 0.0, None
        elif t < INTRO + PER_REGION * len(beats):
            j = int((t - INTRO) // PER_REGION)
            local = (t - INTRO - j * PER_REGION) / PER_REGION
            a, b, k, beat = j, j + 1, ease(local / 0.45), j
        else:
            a, b, k, beat = len(cams) - 2, len(cams) - 1, ease((t - total + OUTRO) / 0.6), None
        ca, cb = cams[a], cams[b]
        cx, cy, z = (lerp(ca[n], cb[n], k) for n in range(3))

        frame = bg.copy()
        crop_w, crop_h = view_w * z, view_h * z
        box = (cx - crop_w / 2, cy - crop_h / 2, cx + crop_w / 2, cy + crop_h / 2)
        view = src.transform((view_w, view_h), Image.EXTENT, box, Image.BICUBIC, fillcolor=INK)
        mask = Image.new("L", (view_w, view_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, view_w, view_h], 28, fill=255)
        frame.paste(view, (24, view_y), mask)
        d = ImageDraw.Draw(frame)
        d.rounded_rectangle([24, view_y, 24 + view_w, view_y + view_h], 28, outline=(60, 60, 84), width=2)

        # Header
        d.text((W / 2, 120), manifest["title"].upper(), font=small_f, fill=MUTED, anchor="ma")
        gradient_text(frame, (W / 2, 170), scene["title"].split("—")[0].strip(), title_f)

        # Caption for the current beat, sliding up
        if beat is not None:
            local = (t - INTRO - beat * PER_REGION) / PER_REGION
            appear = ease(local / 0.35)
            y0 = view_y + view_h + 70 + (1 - appear) * 40
            d.text((W / 2, y0 - 10), f"{beat + 1} / {len(beats)}", font=small_f, fill=PINK, anchor="ma")
            y = y0 + 34
            for line in wrap(d, beats[beat][2], small_f, W - 96)[:3]:
                d.text((W / 2, y), line, font=small_f,
                       fill=tuple(int(c * appear + INK[m] * (1 - appear)) for m, c in enumerate(MUTED)), anchor="ma")
                y += 34
            y += 14
            for line in wrap(d, beats[beat][1], cap_f, W - 96)[:5]:
                col = tuple(int(c * appear + INK[m] * (1 - appear)) for m, c in enumerate(WHITE))
                d.text((W / 2, y), line, font=cap_f, fill=col, anchor="ma")
                y += 52
        elif t >= INTRO:
            gradient_text(frame, (W / 2, view_y + view_h + 120), "Now test yourself", cap_f)
            d.text((W / 2, view_y + view_h + 190), f"{len(beats)} cards waiting", font=small_f, fill=MUTED, anchor="ma")
        else:
            appear = ease(t / 0.8)
            d.text((W / 2, view_y + view_h + 120), "One story. Every fact.", font=cap_f,
                   fill=tuple(int(c * appear + INK[m] * (1 - appear)) for m, c in enumerate(WHITE)), anchor="ma")

        # Progress bar
        p = t / total
        d.rounded_rectangle([24, H - 60, W - 24, H - 54], 3, fill=(40, 40, 56))
        d.rounded_rectangle([24, H - 60, 24 + (W - 48) * p, H - 54], 3, fill=PINK)
        ff.stdin.write(frame.tobytes())

    ff.stdin.close()
    if ff.wait() != 0:
        raise SystemExit("ffmpeg failed")

    scene["video"] = os.path.relpath(out, args.package).replace(os.sep, "/")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"wrote {out} ({total:.1f}s, {len(beats)} beats, {os.path.getsize(out) // 1024} KB)")


if __name__ == "__main__":
    main()
