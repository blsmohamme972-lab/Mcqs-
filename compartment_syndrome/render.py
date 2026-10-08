"""Render an 8-second animated explainer of compartment syndrome with voice-over.

Usage: python3 render.py   (needs Pillow, numpy, ffmpeg; gTTS for the voice-over)
Output: compartment_syndrome.mp4 next to this script.
"""
import math
import os
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, DUR = 1280, 720, 30, 8.0
S = 2  # supersampling factor for anti-aliasing
FONT_DIR = "/usr/share/fonts/opentype/inter"

BG = (14, 22, 38)
PANEL = (24, 35, 58)
WHITE = (240, 244, 250)
MUTED = (150, 165, 190)
SKIN = (233, 190, 160)
SUBQ = (246, 222, 170)
MUSCLE = (200, 82, 92)
MUSCLE_DARK = (120, 70, 110)
FASCIA = (250, 250, 255)
BONE = (240, 232, 210)
MARROW = (215, 190, 140)
ARTERY = (225, 40, 50)
VEIN = (60, 110, 220)
DANGER = (255, 80, 80)
OK = (70, 210, 140)
ACCENT = (255, 196, 60)

# Voice-over lines and their scene windows (seconds). Audio is time-stretched to fit.
VO = [
    ("Compartment syndrome.", 0.10),
    ("Swelling traps pressure in a closed fascial compartment.", 1.20),
    ("Vessels collapse, and muscle starves.", 3.72),
    ("Pain on passive stretch? Urgent fasciotomy!", 5.62),
]
VO_TEMPO = 1.4
SCENES = [0.0, 1.15, 3.70, 5.60, 8.0]


_fonts = {}


def font(size, weight="Bold"):
    key = (size, weight)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(f"{FONT_DIR}/Inter-{weight}.otf", int(size * S))
    return _fonts[key]


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def seg(t, a, b):
    return ease((t - a) / (b - a))


def mix(c1, c2, k):
    k = clamp(k)
    return tuple(int(c1[i] + (c2[i] - c1[i]) * k) for i in range(3))


class D:
    """Drawing helper working in 1280x720 coordinates with an optional transform."""

    def __init__(self, img, ox=0, oy=0, sc=1.0):
        self.img = img
        self.d = ImageDraw.Draw(img)
        self.ox, self.oy, self.sc = ox, oy, sc

    def p(self, x, y):
        return ((self.ox + x * self.sc) * S, (self.oy + y * self.sc) * S)

    def w(self, v):
        return max(1, int(v * self.sc * S))

    def ellipse(self, cx, cy, rx, ry, fill=None, outline=None, width=0):
        x0, y0 = self.p(cx - rx, cy - ry)
        x1, y1 = self.p(cx + rx, cy + ry)
        self.d.ellipse([x0, y0, x1, y1], fill=fill, outline=outline,
                       width=self.w(width) if outline else 0)

    def poly(self, pts, fill=None, outline=None, width=1):
        self.d.polygon([self.p(*q) for q in pts], fill=fill)
        if outline:
            self.line(pts + [pts[0]], outline, width)

    def line(self, pts, fill, width=2):
        self.d.line([self.p(*q) for q in pts], fill=fill, width=self.w(width), joint="curve")

    def text(self, x, y, s, size, fill=WHITE, weight="Bold", anchor="la"):
        f = font(size * self.sc, weight)
        self.d.text(self.p(x, y), s, font=f, fill=fill, anchor=anchor)

    def arrow(self, x0, y0, x1, y1, fill, width=4, head=12):
        self.line([(x0, y0), (x1, y1)], fill, width)
        a = math.atan2(y1 - y0, x1 - x0)
        pts = [(x1, y1),
               (x1 - head * math.cos(a - 0.45), y1 - head * math.sin(a - 0.45)),
               (x1 - head * math.cos(a + 0.45), y1 - head * math.sin(a + 0.45))]
        self.poly(pts, fill=fill)


def ellipse_pts(cx, cy, rx, ry, a0=0, a1=360, n=90):
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


# ---------------------------------------------------------------- components

# Simplified transverse section of the mid-leg (viewer looking from below).
ANT = (520, 300, 78, 62)     # anterior compartment (cx, cy, rx, ry)
LAT = (668, 400, 44, 68)
DEEP = (470, 440, 120, 40)
SUP = (465, 530, 175, 58)


def muscle_blob(dr, comp, col, grow=1.0, dots=True):
    cx, cy, rx, ry = comp
    dr.ellipse(cx, cy, rx * grow, ry * grow, fill=col)
    if dots:
        fib = mix(col, (0, 0, 0), 0.25)
        for i in range(-3, 4):
            for j in range(-2, 3):
                x, y = cx + i * rx * 0.26 * grow, cy + j * ry * 0.33 * grow
                if ((x - cx) / (rx * grow)) ** 2 + ((y - cy) / (ry * grow)) ** 2 < 0.7:
                    dr.ellipse(x, y, 3, 3, fill=fib)


def cross_section(dr, swell=0.0, open_amt=0.0, labels=1.0, pulse=0.0):
    """swell: 0..1 edema in anterior compartment; open_amt: 0..1 fasciotomy."""
    dr.ellipse(470, 405, 255, 215, fill=SKIN)
    dr.ellipse(470, 405, 238, 198, fill=SUBQ)
    # fasciotomy skin incision (wedge over anterolateral leg)
    if open_amt > 0:
        g = 0.22 * open_amt
        dr.poly(ellipse_pts(470, 405, 256, 216, -62 - g * 40, -62 + g * 40, 20) + [(560, 290)], fill=(150, 30, 40))
    for comp in (SUP, DEEP, LAT):
        muscle_blob(dr, comp, MUSCLE)
        dr.ellipse(*comp, outline=FASCIA, width=3)
    # anterior compartment: swells against an unyielding fascia
    ant_col = mix(MUSCLE, (165, 30, 45), swell * (1 - open_amt))
    grow = 0.86 + 0.14 * swell
    if open_amt > 0:
        grow = 1.0 + 0.12 * open_amt
    cx, cy, rx, ry = ANT
    shift = 10 * open_amt
    muscle_blob(dr, (cx + shift * 0.5, cy - shift, rx, ry), ant_col, grow)
    # vessels on the interosseous membrane
    vsq = clamp(swell * 1.6 - 0.2) * (1 - open_amt)
    dr.ellipse(505, 352, 9, 9 * (1 - 0.75 * vsq), fill=VEIN)
    dr.ellipse(525, 352, 8, 8 * (1 - 0.45 * clamp(vsq * 1.3 - 0.4)), fill=ARTERY)
    # fascia outline (thickens / glows with pressure, splits open on fasciotomy)
    fw = 3 + 3 * swell * (1 - open_amt) + 2 * pulse
    fcol = mix(FASCIA, ACCENT, swell * (1 - open_amt))
    if open_amt <= 0:
        dr.ellipse(*ANT, outline=fcol, width=fw)
    else:
        gap = 70 * open_amt
        dr.line(ellipse_pts(cx, cy, rx, ry, -60 + gap / 2, 300 - gap / 2), fcol, fw)
    # bones and interosseous membrane
    dr.line([(430, 345), (650, 395)], (220, 220, 230), 3)
    dr.ellipse(405, 320, 58, 52, fill=BONE)
    dr.ellipse(405, 322, 30, 26, fill=MARROW)
    dr.ellipse(640, 398, 24, 24, fill=BONE)
    dr.ellipse(640, 398, 10, 10, fill=MARROW)
    if labels > 0:
        lc = mix(BG, WHITE, labels)
        dr.text(405, 320, "Tibia", 14, (90, 70, 40), anchor="mm")
        dr.text(520, 300 - 4, "Anterior", 15, lc, anchor="mm")
        dr.text(668, 446, "Lat.", 15, lc, anchor="mm")
        dr.text(470, 442, "Deep posterior", 15, lc, anchor="mm")
        dr.text(465, 540, "Superficial posterior", 15, lc, anchor="mm")
    # inward pressure arrows: the fascia will not stretch
    if swell > 0.15 and open_amt < 0.5:
        k = clamp((swell - 0.15) / 0.5) * (1 - 2 * open_amt)
        col = mix(BG, DANGER, k)
        for ang in (200, 250, 300, 340, 20):
            a = math.radians(ang)
            ox, oy = cx + (rx + 30) * math.cos(a), cy + (ry + 30) * math.sin(a)
            ix, iy = cx + (rx + 6) * math.cos(a), cy + (ry + 6) * math.sin(a)
            dr.arrow(ox, oy, ix, iy, col, 4, 11)


def gauge(dr, value, t):
    cx, cy, r = 1020, 250, 112
    dr.ellipse(cx, cy, r + 22, r + 22, fill=PANEL)

    def pt(v, rr):
        th = math.radians(225 - 270 * v / 60)
        return cx + rr * math.cos(th), cy - rr * math.sin(th)

    dr.line([pt(v / 2, r) for v in range(0, 61)], (70, 85, 115), 14)
    dr.line([pt(v / 2, r) for v in range(60, 121)], (150, 45, 55), 14)
    for v in range(0, 61, 10):
        dr.line([pt(v, r - 14), pt(v, r - 24)], MUTED, 3)
        dr.text(*pt(v, r - 40), str(v), 14, MUTED, "Medium", anchor="mm")
    col = DANGER if value >= 30 else OK
    dr.line([(cx, cy), pt(value, r - 18)], col, 6)
    dr.ellipse(cx, cy, 10, 10, fill=col)
    dr.text(cx, cy + r + 52, f"{value:.0f} mmHg", 30, col, anchor="mm")
    dr.text(cx, cy + r + 82, "compartment pressure", 15, MUTED, "Medium", anchor="mm")
    if value >= 30 and int(t * 4) % 2 == 0:
        dr.text(cx, cy - 34, "> 30", 18, DANGER, anchor="mm")


def caption_panel(dr, title, body, k, color=WHITE):
    if k <= 0:
        return
    y = 470 + 18 * (1 - k)
    c = mix(BG, color, k)
    m = mix(BG, MUTED, k)
    dr.text(820, y, title, 28, c)
    for i, line in enumerate(body):
        dr.text(820, y + 44 + i * 28, line, 19, m, "Medium")


def subtitle(dr, text, k):
    if not text or k <= 0:
        return
    f = font(22, "SemiBold")
    tw = dr.d.textlength(text, font=f) / S
    x0, x1 = 640 - tw / 2 - 18, 640 + tw / 2 + 18
    bg = mix(BG, (0, 0, 0), 0.6 * k)
    dr.d.rounded_rectangle([x0 * S, 660 * S, x1 * S, 700 * S], radius=10 * S, fill=bg)
    dr.text(640, 681, text, 22, mix(BG, WHITE, k), "SemiBold", anchor="mm")


def zoom_view(dr, k, t):
    """Close-up of the anterior compartment: vein, then artery, collapse."""
    x0, y0, x1, y1 = 90, 150, 760, 590
    dr.d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], radius=28 * S,
                           fill=PANEL, outline=mix(FASCIA, ACCENT, 1), width=6 * S)
    musc = mix(MUSCLE, MUSCLE_DARK, seg(k, 0.45, 1.0))
    for row in range(5):
        y = 185 + row * 26
        dr.d.rounded_rectangle([130 * S, y * S, 720 * S, (y + 16) * S], radius=8 * S, fill=musc)
        y = 455 + row * 26
        dr.d.rounded_rectangle([130 * S, y * S, 720 * S, (y + 16) * S], radius=8 * S, fill=musc)
    vein_h = 26 * (1 - 0.85 * seg(k, 0.0, 0.4))
    art_h = 22 * (1 - 0.7 * seg(k, 0.35, 0.8))
    vy, ay = 340, 405
    dr.d.rounded_rectangle([110 * S, (vy - vein_h) * S, 740 * S, (vy + vein_h) * S],
                           radius=int(vein_h * S), fill=VEIN)
    dr.d.rounded_rectangle([110 * S, (ay - art_h) * S, 740 * S, (ay + art_h) * S],
                           radius=int(art_h * S), fill=ARTERY)
    # blood cells slow down as lumens close
    flow = 1 - seg(k, 0.3, 0.9)
    for i in range(9):
        x = 120 + ((i * 72 + t * 260 * flow) % 610)
        dr.ellipse(x, ay, 8 * art_h / 22, 5 * art_h / 22, fill=(255, 150, 150))
    dr.text(130, vy, "vein", 18, WHITE, anchor="lm")
    dr.text(130, ay, "artery", 18, WHITE, anchor="lm")
    for x in (230, 425, 620):
        dr.arrow(x, 160, x, 182, DANGER, 5, 12)
        dr.arrow(x, 580, x, 558, DANGER, 5, 12)
    if k > 0.6:
        a = seg(k, 0.6, 0.85)
        dr.d.rounded_rectangle([330 * S, 352 * S, 520 * S, 393 * S], radius=12 * S, fill=mix(PANEL, (10, 10, 20), a))
        dr.text(425, 373, "ISCHEMIA", 26, mix(PANEL, ACCENT, a), anchor="mm")


def leg_side(dr, k, t):
    """Side view of leg: passive plantarflexion stretches the anterior compartment."""
    dr.d.rounded_rectangle([330 * S, 140 * S, 440 * S, 470 * S], radius=45 * S, fill=SKIN)
    sw = 0.5 + 0.5 * math.sin(t * 12)
    dr.ellipse(408, 300, 26, 95, fill=mix(MUSCLE, (170, 25, 40), 0.6 + 0.4 * sw))
    dr.text(470, 160, "anterior compartment", 16, MUTED, "Medium")
    dr.line([(468, 168), (420, 220)], MUTED, 2)
    ang = math.radians(32 * seg(k, 0.1, 0.6))
    ax, ay = 385, 455
    foot = [(-55, -15), (55, -10), (130, 5), (165, 20), (168, 38), (-50, 45), (-62, 20)]
    pts = [(ax + x * math.cos(ang) - y * math.sin(ang), ay + x * math.sin(ang) + y * math.cos(ang))
           for x, y in foot]
    dr.poly(pts, fill=SKIN)
    # examiner's push on the toes
    tx, ty = pts[3]
    dr.arrow(tx + 60, ty - 70, tx + 12, ty - 10, ACCENT, 6, 16)
    dr.text(tx + 66, ty - 92, "passive stretch", 18, ACCENT)
    # pain burst over shin
    if k > 0.35:
        r = 34 + 8 * sw
        star = [(500 + (r if i % 2 == 0 else r * 0.5) * math.cos(i * math.pi / 8),
                 290 + (r if i % 2 == 0 else r * 0.5) * math.sin(i * math.pi / 8)) for i in range(16)]
        dr.poly(star, fill=DANGER)
        dr.text(500, 290, "!", 30, WHITE, anchor="mm")
        dr.text(500, 345, "PAIN", 20, DANGER, anchor="mm")


# ---------------------------------------------------------------- timeline

def pressure_at(t):
    if t < 1.15:
        return 8
    if t < 3.7:
        return 8 + 40 * seg(t, 1.4, 3.4)
    if t < 6.7:
        return 48 + 3 * math.sin(t * 9)
    return 48 - 38 * seg(t, 6.9, 7.7)


def scene_frame(t):
    img = Image.new("RGB", (W * S, H * S), BG)
    dr = D(img)
    if t < 3.7:
        sk = seg(t, 0.0, 0.5)
        sub = D(img, 470 * (1 - (0.88 + 0.12 * sk)), 405 * (1 - (0.88 + 0.12 * sk)), 0.88 + 0.12 * sk)
        swell = seg(t, 1.4, 3.3)
        cross_section(sub, swell=swell, labels=seg(t, 0.3, 0.8), pulse=0.5 + 0.5 * math.sin(t * 14) if swell > 0.5 else 0)
    elif t < 5.6:
        zoom_view(dr, seg(t, 3.75, 5.4), t)
    elif t < 6.75:
        leg_side(dr, seg(t, 5.6, 6.6), t)
    else:
        k = seg(t, 6.85, 7.6)
        cross_section(dr, swell=1.0, open_amt=k, labels=0.0)
        # dashed incision guide
        if k < 1:
            for i in range(6):
                a = math.radians(-95 + i * 9)
                x, y = 470 + 270 * math.cos(a), 405 + 232 * math.sin(a)
                if i % 2 == 0:
                    dr.line([(x, y), (470 + 270 * math.cos(a + 0.12), 405 + 232 * math.sin(a + 0.12))],
                            mix(BG, ACCENT, 1 - k), 4)

    gauge(dr, pressure_at(t), t)

    # right-hand captions per scene
    if t < 1.15:
        k = seg(t, 0.05, 0.45)
        dr.text(820, 470 + 16 * (1 - k), "Compartment", 44, mix(BG, WHITE, k))
        dr.text(820, 522 + 16 * (1 - k), "Syndrome", 44, mix(BG, ACCENT, k))
        dr.text(820, 585, "Cross-section of the mid-leg", 18, mix(BG, MUTED, k), "Medium")
    elif t < 3.7:
        caption_panel(dr, "Pressure builds",
                      ["Fracture, crush or tight cast →", "swelling inside fascia that", "cannot stretch"],
                      seg(t, 1.2, 1.6))
    elif t < 5.6:
        caption_panel(dr, "Perfusion fails",
                      ["1. Veins collapse first", "2. Then arterioles", "3. Muscle & nerve ischemia"],
                      seg(t, 3.75, 4.1), DANGER)
    elif t < 6.75:
        caption_panel(dr, "Earliest sign",
                      ["Pain out of proportion,", "worse on passive stretch.", "Pulses often still present!"],
                      seg(t, 5.65, 5.95), ACCENT)
    else:
        caption_panel(dr, "Treatment",
                      ["Urgent fasciotomy", "Split fascia → pressure falls", "→ perfusion restored"],
                      seg(t, 6.8, 7.1), OK)

    # subtitles follow the voice-over
    for i, (line, start) in enumerate(VO):
        end = VO[i + 1][1] if i + 1 < len(VO) else DUR
        if start <= t < end:
            subtitle(dr, line, seg(t, start, start + 0.15) * (1 - seg(t, end - 0.1, end)) if i + 1 < len(VO)
                     else seg(t, start, start + 0.15))

    # progress bar
    dr.d.rectangle([0, (H - 5) * S, int(W * S * t / DUR), H * S], fill=ACCENT)
    return img.resize((W, H), Image.LANCZOS)


def frame(t):
    # short cross-fades between scenes
    for b in SCENES[1:-1] + [6.75]:
        if b - 0.12 <= t < b + 0.12:
            a = scene_frame(b - 0.121)
            c = scene_frame(b + 0.001)
            return Image.blend(a, c, (t - (b - 0.12)) / 0.24)
    return scene_frame(t)


# ---------------------------------------------------------------- voice-over

def build_voiceover(tmp):
    from gtts import gTTS
    inputs, filters = [], []
    for i, (line, start) in enumerate(VO):
        mp3 = os.path.join(tmp, f"vo{i}.mp3")
        gTTS(line, lang="en", tld="com").save(mp3)
        inputs += ["-i", mp3]
        filters.append(
            f"[{i}]silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
            f"silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
            f"atempo={VO_TEMPO},adelay={int(start * 1000)}:all=1[a{i}]")
    mix_in = "".join(f"[a{i}]" for i in range(len(VO)))
    fc = ";".join(filters) + f";{mix_in}amix=inputs={len(VO)}:normalize=0,apad,atrim=0:{DUR},loudnorm=I=-16[out]"
    wav = os.path.join(tmp, "voiceover.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc,
                    "-map", "[out]", "-ar", "44100", wav], check=True)
    return wav


def main():
    tmp = tempfile.mkdtemp()
    try:
        n = int(DUR * FPS)
        for i in range(n):
            frame(i / FPS).save(os.path.join(tmp, f"f{i:04d}.png"))
            if i % 30 == 0:
                print(f"frame {i}/{n}", file=sys.stderr)
        wav = build_voiceover(tmp)
        out = os.path.join(HERE, "compartment_syndrome.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS),
                        "-i", os.path.join(tmp, "f%04d.png"), "-i", wav,
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                        "-c:a", "aac", "-b:a", "160k", "-t", str(DUR),
                        "-movflags", "+faststart", out], check=True)
        print(out)
    finally:
        shutil.rmtree(tmp)


if __name__ == "__main__":
    main()
