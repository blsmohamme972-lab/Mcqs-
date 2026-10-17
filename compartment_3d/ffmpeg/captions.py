"""Write burn-in subtitles (ASS) for the lesson video, one file per orientation.

The caption text and timings are read from CAPTIONS in ../compartment_3d.src.html,
so the page and the video always say the same thing. English words appear one by
one (karaoke tags, 0.11 s per word, the same pace as the page); the Arabic line
fades in 0.3 s later. libass shapes the Arabic right to left (fribidi + harfbuzz).

Usage: python captions.py <out dir>   -> captions_16x9.ass, captions_9x16.ass
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "compartment_3d.src.html")
WORD = 0.11  # seconds per revealed word, as in the page

# key-term colours from the page's tokens (RRGGBB)
KEY = {"ant": "35c3b6", "danger": "ff4040", "ok": "4fd68b", "nerve": "ffd54f"}

ORIENT = {
    # name: (PlayResX, PlayResY, en size, ar size, title size, bottom margin, side margin)
    "16x9": (1920, 1080, 62, 44, 118, 70, 160),
    "9x16": (1080, 1920, 60, 44, 104, 330, 70),
}


def ass_colour(rrggbb, alpha="00"):
    r, g, b = rrggbb[0:2], rrggbb[2:4], rrggbb[4:6]
    return f"&H{alpha}{b}{g}{r}".upper()


def ts(sec):
    cs = round(sec * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def read_captions():
    js = open(SRC, encoding="utf-8").read()
    block = js[js.index("const CAPTIONS = ["):]
    block = block[: block.index("];")]
    pat = re.compile(r"\{ a: ([\d.]+), b: ([\d.]+),( title: true,)? en: '([^']*)', ar: '([^']*)' \}")
    caps = [dict(a=float(m[1]), b=float(m[2]), title=bool(m[3]), en=m[4], ar=m[5]) for m in pat.finditer(block)]
    if not caps:
        sys.exit("no captions found in " + SRC)
    return caps


def karaoke(en):
    """'[ant:anterior compartment.] climbs' -> per-word \\k tags with key-term colours."""
    out = []
    for tok in re.findall(r"\[(\w+):([^\]]+)\]|(\S+)", en):
        kind, marked, plain = tok
        words = marked.split() if kind else [plain]
        colour = r"{\1c" + ass_colour(KEY[kind]) + "&}" if kind else ""
        reset = r"{\1c&HFFFFFF&}" if kind else ""
        for w in words:
            out.append(r"{\k" + str(round(WORD * 100)) + "}" + colour + w + reset)
    return " ".join(out)


def write(name, caps, out_dir):
    w, h, en_size, ar_size, title_size, mv, ml = ORIENT[name]
    white, hidden, shadow = ass_colour("FFFFFF"), ass_colour("FFFFFF", "FF"), ass_colour("000000", "60")
    ar_col = ass_colour("C9D6E2")
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {w}", f"PlayResY: {h}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        # SecondaryColour fully transparent: karaoke words stay invisible until their \k time
        f"Style: EN,Archivo,{en_size},{white},{hidden},{shadow},{shadow},-1,0,0,0,92,100,0,0,1,0,6,2,{ml},{ml},{mv + int(ar_size * 1.9)},1",
        f"Style: Title,Archivo,{title_size},{white},{hidden},{shadow},{shadow},-1,0,0,0,80,100,0,0,1,0,8,2,{ml},{ml},{mv + int(ar_size * 2.2)},1",
        f"Style: AR,IBM Plex Sans Arabic,{ar_size},{ar_col},{ar_col},{shadow},{shadow},0,0,0,0,100,100,0,0,1,0,5,2,{ml},{ml},{mv},178",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for c in caps:
        style = "Title" if c["title"] else "EN"
        lines.append(f"Dialogue: 0,{ts(c['a'])},{ts(c['b'])},{style},,0,0,0,,{{\\fad(0,250)}}{karaoke(c['en'])}")
        lines.append(f"Dialogue: 0,{ts(c['a'] + 0.3)},{ts(c['b'])},AR,,0,0,0,,{{\\fad(400,250)}}{c['ar']}")
    path = os.path.join(out_dir, f"captions_{name}.ass")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(path, len(caps), "captions")


if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else HERE
    os.makedirs(out_dir, exist_ok=True)
    caps = read_captions()
    for name in ORIENT:
        write(name, caps, out_dir)
