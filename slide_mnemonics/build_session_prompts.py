"""Fill SLIDE_SESSION.md for every extracted slide of a deck.

Usage:
  python3 build_session_prompts.py slides/<deck> --branch <git-branch> [--slides 1,3-5]

Writes slides/<deck>/slide_NN/session_prompt.md: the full first message for that
slide's session.
"""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).parent


def pick(spec, total):
    if not spec:
        return list(range(1, total + 1))
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += range(int(a), int(b or a) + 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deck_dir", type=Path)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--slides", help="e.g. 1,3-5 (default: all)")
    a = ap.parse_args()

    template = (HERE / "SLIDE_SESSION.md").read_text()
    slides = json.loads((a.deck_dir / "slides.json").read_text())
    for n in pick(a.slides, len(slides)):
        d = a.deck_dir / f"slide_{n:02d}"
        content = (d / "content.md").read_text().strip()
        title = slides[n - 1]["title"] or f"Slide {n}"
        text = (template.replace("{{N}}", f"{n:02d}").replace("{{TITLE}}", title)
                .replace("{{DECK}}", a.deck_dir.name).replace("{{BRANCH}}", a.branch)
                .replace("{{CONTENT}}", content))
        (d / "session_prompt.md").write_text(text)
        print(d / "session_prompt.md")


if __name__ == "__main__":
    main()
