"""Book lessons: one landscape illustration + one voice that explains one topic of the book (about a minute).

Same engine as the Kafu image lessons (motioncards/lib/lesson.py builds the scene, the voice track and the entry HTML),
but the source is a topic of our book, not an MCQ: no question, no answer key, no QID from the bot. Package format:
`booklessons-manifest.json` (package_type "mcqs-booklessons") + `entries/<qid>.html`, read by the Android app.
"""
from __future__ import annotations
import hashlib, json, re, zipfile
from pathlib import Path

PACKAGE_TYPE = "mcqs-booklessons"
MANIFEST = "booklessons-manifest.json"
STAGE_W, STAGE_H = 960, 540
STYLE = ("Landscape 16:9 illustration, flat colourful cartoon (Picmonic / Sketchy style), clean white background, crisp thick outlines. "
         "All text sits in rounded white label boxes with dark navy bold letters, crisp and spelled exactly as given. ")
STORY_RULES = ("STORY RULES FOR THIS IMAGE (must, not optional): this is a Picmonic / Sketchy visual mnemonic. ONE story with ONE MAIN CHARACTER "
               "in the centre of the picture. Every other character is part of that same story: it touches, helps, attacks, feeds, chases or talks "
               "to the MAIN CHARACTER, all in one place at one moment. Each character is a clever sound-alike or look-alike pun whose look, clothes "
               "or prop shows its ONE fact, so a student who remembers the story remembers every fact. Make the characters wonderful: funny, "
               "expressive, exaggerated, with a small joke. No character stands alone or unrelated; no separate panels; no list of icons.")


def qid_for(chapter: int, n: int) -> str:
    """Synthetic 10-character id that passes the lesson engine's Q+9-digit rule: Q9 CC NN 0000 (book lessons never collide with bot QIDs)."""
    if not (1 <= chapter <= 99 and 1 <= n <= 99): raise ValueError("chapter/topic out of range")
    return f"Q9{chapter:02d}{n:02d}0000"


def line_obj(line) -> dict:
    return {"text": line} if isinstance(line, str) else {k: line[k] for k in ("text", "say") if k in line}


def split_long(obj: dict, limit: int = 190) -> list[dict]:
    """The engine takes lines of at most 200 characters: break longer ones after a comma (the spoken form is split the same way)."""
    if len(obj["text"]) <= limit and len(obj.get("say", "")) <= limit: return [obj]
    def cut(s):
        i = s.rfind(", ", 0, limit)
        return (s[:i + 1], s[i + 2:]) if i > 40 else (s[:limit].rsplit(" ", 1)[0], s[len(s[:limit].rsplit(" ", 1)[0]) + 1:])
    a, b = cut(obj["text"]); out = {"text": a}; rest = {"text": b}
    if "say" in obj:
        sa, sb = cut(obj["say"]); out["say"], rest["say"] = sa, sb
    return [out] + split_long(rest, limit)


def auto_shots(w: int, h: int, n_lines: int) -> tuple[list[dict], list[int]]:
    """Whole picture for the first line, then slow zooms over the four quarters; returns (shots, shot index per line)."""
    shots = [{"x": w / 2, "y": h / 2, "z": 1}]
    for cx, cy in ((.3, .35), (.7, .35), (.3, .62), (.7, .62)):
        shots.append({"x": w * cx, "y": h * cy, "z": 1.7})
    order = [0] + [1 + (i - 1) % 4 for i in range(1, n_lines)]
    return shots, order


def lesson_spec(topic: dict, qid: str, image_name: str, w: int, h: int, engine: str) -> dict:
    lines = [p for l in topic["lines"] for p in split_long(line_obj(l))]
    shots, order = auto_shots(w, h, len(lines))
    for ln, s in zip(lines, order): ln["shot"] = s
    return {"qid": qid, "image": image_name, "takeaway": topic["takeaway"][:240], "engine": engine, "tempo": 1.0, "shots": shots, "lines": lines}


def prompt_for(topic: dict, chapter_title: str) -> str:
    facts = "\n".join(f"- {(l if isinstance(l, str) else l['text'])}" for l in topic["lines"])
    return (f"{STYLE}\nTOPIC: {topic['title']}  (book: Cardiothoracic Surgery 2e, chapter: {chapter_title}, pages {topic['pages']}).\n"
            f"Teach exactly these facts, no others; every label text must come from them:\n{facts}\n{STORY_RULES}\n")


def build_package(workspace: Path, chapter: dict, built: list[dict], out_zip: Path, revision: int = 1) -> dict:
    """built: [{topic, qid}] whose scenes/voice exist in the workspace. Writes the zip and returns the manifest."""
    from motioncards.lib.compiler import compile_scene
    files: dict[str, bytes] = {}; rows = []
    for b in built:
        qid = b["qid"]; t = b["topic"]
        scene = json.loads((workspace / "scenes" / f"{qid}.scene.json").read_text(encoding="utf-8"))
        audio = (workspace / "voice" / f"{qid}.opus").read_bytes(); track = json.loads((workspace / "voice" / f"{qid}.track.json").read_text(encoding="utf-8"))
        html = compile_scene(scene, voice=audio).encode()
        path = f"entries/{qid}.html"; files[path] = html
        rows.append({"id": t["id"], "qid": qid, "title": t["title"], "pages": t["pages"], "chapter": chapter["chapter"], "takeaway": scene["takeaway"],
                     "duration_ms": scene["duration_ms"], "entry_path": path, "entry_sha256": hashlib.sha256(html).hexdigest(),
                     "voice_bytes": len(audio), "cues": len(track.get("cues", []))})
    manifest = {"package_type": PACKAGE_TYPE, "schema_version": 1, "package_id": chapter["package_id"], "package_revision": revision,
                "book": chapter["book"], "chapter": chapter["chapter"], "chapter_title": chapter["chapter_title"], "lessons": rows}
    files[MANIFEST] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in sorted(files.items()):
            zi = zipfile.ZipInfo(name); zi.date_time = (2026, 1, 1, 0, 0, 0); zi.compress_type = zipfile.ZIP_DEFLATED; zi.external_attr = 0o100644 << 16
            z.writestr(zi, data)
    return manifest
