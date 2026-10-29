#!/usr/bin/env python3
"""Book lessons: an image + voice that explains one topic of the book (about one minute).

  booklessons.py prompts  ch01 [--out work/BOOK-CH01]     one ChatGPT image prompt per topic -> prompts/<id>.txt
  booklessons.py build    ch01 [--engine breeze|kokoro|elevenlabs] [--only id ...]
                                         for every topic whose image is work/<pkg>/images/<id>.png (or .jpg/.webp):
                                         writes lessons/<QID>.lesson.json, then speaks and builds scene + voice (voice venv python)
  booklessons.py package  ch01 [--revision N]   -> work/<pkg>/BOOK-CH01_r<N>.zip  (only built topics)
  booklessons.py status   ch01                  which topics have prompt / image / voice
Owner's rules (CLAUDE.md): ask which voice engine and who renders before `build`; commit only text, never images/voice/zips.
"""
import argparse, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from booklessons import lib  # noqa: E402

IMG_EXT = (".png", ".jpg", ".jpeg", ".webp")


def load(ch: str) -> dict:
    return json.loads((ROOT / "booklessons" / "chapters" / f"{ch}.json").read_text(encoding="utf-8"))


def image_of(ws: Path, topic: dict):
    for e in IMG_EXT:
        p = ws / "images" / f"{topic['id']}{e}"
        if p.is_file(): return p
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["prompts", "build", "package", "status"]); ap.add_argument("chapter")
    ap.add_argument("--out", type=Path); ap.add_argument("--engine"); ap.add_argument("--only", nargs="*"); ap.add_argument("--revision", type=int, default=1)
    a = ap.parse_args(); ch = load(a.chapter); ws = a.out or ROOT / "work" / ch["package_id"]
    topics = [t for t in ch["topics"] if not a.only or t["id"] in a.only]
    for sub in ("prompts", "images", "lessons", "scenes", "voice"): (ws / sub).mkdir(parents=True, exist_ok=True)
    if a.cmd == "prompts":
        for t in topics: (ws / "prompts" / f"{t['id']}.txt").write_text(lib.prompt_for(t, ch["chapter_title"]), encoding="utf-8")
        print(f"{len(topics)} prompts in {ws/'prompts'}; save each picture as {ws/'images'}/<id>.png")
    elif a.cmd == "status":
        for t in topics:
            q = lib.qid_for(ch["chapter"], t["n"])
            print(f"{t['id']:34} {q}  prompt={'y' if (ws/'prompts'/(t['id']+'.txt')).exists() else '-'} image={'y' if image_of(ws, t) else '-'} voice={'y' if (ws/'voice'/(q+'.opus')).exists() else '-'}")
    elif a.cmd == "build":
        if not a.engine: sys.exit("--engine is required: ask the owner which voice engine (kokoro | breeze | elevenlabs)")
        sel = ws / "selection.json"; rows = []
        from motioncards.lib.lesson import build_lesson, _image_size
        for t in topics:
            img = image_of(ws, t)
            if not img: print("skip (no image):", t["id"]); continue
            q = lib.qid_for(ch["chapter"], t["n"]); w, h = _image_size(img)
            (ws / "lessons" / f"{q}.lesson.json").write_text(json.dumps(lib.lesson_spec(t, q, "../images/" + img.name, w, h, a.engine), ensure_ascii=False, indent=1), encoding="utf-8")
            rows.append({"qid": q, "duration_ms": 60000})
            sel.write_text(json.dumps({"selected": rows}), encoding="utf-8")
            print(json.dumps(build_lesson(ws, q)))
    else:
        built = [{"topic": t, "qid": lib.qid_for(ch["chapter"], t["n"])} for t in topics]
        built = [b for b in built if (ws / "scenes" / f"{b['qid']}.scene.json").exists() and (ws / "voice" / f"{b['qid']}.opus").exists()]
        if not built: sys.exit("nothing built yet: run `build` first")
        z = ws / f"{ch['package_id']}_r{a.revision}.zip"; m = lib.build_package(ws, ch, built, z, a.revision)
        print(f"{z}  {len(m['lessons'])} lessons, {z.stat().st_size/1e6:.1f} MB")


if __name__ == "__main__":
    main()
