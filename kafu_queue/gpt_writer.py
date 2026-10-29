#!/usr/bin/env python3
"""ChatGPT step 1: the prompts the owner pastes into ChatGPT so that it WRITES the image prompts.

  python3 kafu_queue/gpt_writer.py --prefix GT-CH5 --out writer_GT-CH5.html [--per-chat 8] [--set 8] [--qids Q..,Q..]

Reads queue/<PREFIX>-*.json (make_queue.py split) and writes one HTML page for the owner: one card per ChatGPT chat,
each with a "Copy" button. A card holds the writing rules, the questions (stem, options, key, explanation) and a
Python script. ChatGPT fills in only the DATA part of the script (per question: a title, Picmonic/Sketchy-style
scenes and a banner per question) and runs it. The script checks the work (every QID once, every banner present, short
answers copied exactly) and writes painter_<first>-<last>.html: one card per set of 8 images, each card a complete
message for a NEW ChatGPT chat that draws the 8 images and saves them to Google Drive as <QID>.png.

The same page code (PAGE_CODE) builds both HTML files, so the owner sees the same Copy page twice.
"""
import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from kafu_data import CONFIG, QUEUE  # noqa: E402
EXACT_MAX = 60      # an answer up to this many characters must appear on the banner exactly as written

# Builds a Copy page. Used here and pasted verbatim into the script ChatGPT runs. Plain Python, no imports beyond json/html.
PAGE_CODE = r'''
import html as _html, json as _json

def copy_page(title, intro, cards):
    """cards: list of (heading, text). Returns one self-contained HTML page with a Copy button per card."""
    css = ("body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;padding:16px;background:#f4f6fa;color:#111}"
           "h1{font-size:20px;margin:0 0 6px}p.i{margin:0 0 14px;color:#444;font-size:14px}"
           ".c{background:#fff;border:1px solid #d6dbe4;border-radius:10px;padding:12px;margin:0 0 14px}"
           ".h{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap}"
           ".h b{font-size:16px}button{font-size:16px;padding:10px 18px;border:0;border-radius:8px;background:#1f5eff;color:#fff}"
           "button.ok{background:#14883e}textarea{width:100%;box-sizing:border-box;height:120px;margin-top:8px;font:12px monospace}"
           "@media (prefers-color-scheme:dark){body{background:#111418;color:#eee}.c{background:#1b2027;border-color:#2c333d}"
           "p.i{color:#aaa}textarea{background:#0d1014;color:#ddd}}")
    js = ("var T=" + _json.dumps([t for _, t in cards]).replace("</", "<\\/") + ";"
          "function cp(i,b){var t=T[i];function done(){b.textContent='Copied \\u2713';b.className='ok';}"
          "function fb(){var a=document.getElementById('t'+i);a.focus();a.select();try{document.execCommand('copy');done();}"
          "catch(e){b.textContent='Select the text below and copy';}}"
          "if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(t).then(done,fb);}else{fb();}}")
    out = ["<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
           "<title>" + _html.escape(title) + "</title><style>" + css + "</style></head><body>",
           "<h1>" + _html.escape(title) + "</h1><p class='i'>" + _html.escape(intro) + "</p>"]
    for i, (head, text) in enumerate(cards):
        out.append("<div class='c'><div class='h'><b>" + _html.escape(head) + " (" + str(len(text)) + " chars)</b>"
                   "<button onclick='cp(" + str(i) + ",this)'>Copy</button></div>"
                   "<textarea id='t" + str(i) + "' readonly>" + _html.escape(text) + "</textarea></div>")
    out.append("<script>" + js + "</script></body></html>")
    return "".join(out)
'''

STORY_RULES = ("STORY RULES FOR THIS IMAGE (must, not optional): this is a Picmonic / Sketchy visual mnemonic. ONE story with ONE MAIN CHARACTER in the centre of the picture. Every other character is part of that same story: it touches, helps, attacks, feeds, chases or talks to the MAIN CHARACTER, all in one place at one moment. Each character is a clever sound-alike or look-alike pun whose look, clothes or prop shows its ONE fact, so a student who remembers the story remembers every fact. Make the characters wonderful: funny, expressive, exaggerated, with a small joke. No character stands alone or unrelated; no separate panels; no list of icons.")
# Every image prompt carries STYLE, so the story rules travel with it (owner's rule: Picmonic / Sketchy, one story, one main character).
STYLE = ("Picmonic-style visual mnemonic, fun and medically accurate, for medical students: cute cartoon characters with big "
         "friendly eyes, bright flat colors, thick dark outlines, clean pale background, each fact drawn as a memorable visual pun. "
         "All text sits in rounded white label boxes with dark navy bold letters, crisp and spelled exactly as given. " + STORY_RULES)
AVOID = ("Avoid: garbled or misspelled text, extra text that is not in quotes here, duplicated characters, distorted faces, "
         "realistic gore, photographs, watermarks, cluttered dark background.")
FRESH = ('IMPORTANT - FRESH START: ignore any images, files or results from previous chats or from your memory. Do not reuse, '
         'link to or re-upload any old image. The ONLY truth is what is in the Google Drive folder "@@DRIVE_NAME@@" right now '
         '(not the trash). Every image in this task must be newly generated in this chat.')

# Shared by both scripts ChatGPT may run: constants, the Copy page, and make_page (checks DATA, writes painter_*.html).
CORE = r'''EXACT_MAX = @@EXACT_MAX@@
DRIVE = "@@DRIVE@@"
DRIVE_NAME = "@@DRIVE_NAME@@"
STYLE = @@STYLE@@
AVOID = @@AVOID@@
FRESH = @@FRESH@@
@@PAGE_CODE@@

def norm(t):
    import re
    t = str(t).lower().replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    t = t.replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"[\s]+", " ", re.sub(r"[^\w%'\-./ ]+", " ", t)).strip()


EVENTS = ("(laugh)", "(sigh)", "(clears throat)")
VOICE_KEYS = {"question", "question_say", "answer", "answer_say", "lines", "remember", "takeaway"}
LINE_KEYS = {"text", "say", "scene", "dir"}
WORDS_PER_SECOND = 2.5          # Breeze reads about 2.5 words per second at tempo 1.0
MAX_SECONDS = 60                # owner's rule: one question's voice is at most 60 seconds


def _spoken(d):
    return str(d.get("say") or d.get("text") or "")


def voice_seconds(v):
    """Rough length: the words spoken, plus the app's fixed pauses (lead 0.5 s, tail 0.6 s, 1.1 s after the answer,
    0.45 s between parts)."""
    import re
    parts = [str(v.get("question_say") or v.get("question") or ""), str(v.get("answer_say") or v.get("answer") or "")]
    parts += [_spoken(x) for x in v.get("lines") or [] if isinstance(x, dict)]
    if isinstance(v.get("remember"), dict):
        parts.append(_spoken(v["remember"]))
    words = sum(len(re.sub(r"\([a-z ]+\)", " ", p).split()) for p in parts)
    return round(words / WORDS_PER_SECOND + 2.2 + 0.45 * (len(parts) - 1), 1)


def numbers_in(t):
    """The numbers written in a text (T10 -> 10, 3 x 4 cm -> 3, 4)."""
    import re
    return set(re.findall(r"\d+(?:\.\d+)?", str(t)))


def wrong_in(text, wrong, key_text):
    """The wrong options whose words appear in text (whole words; options that are part of the key do not count)."""
    import re
    t, k, hit = norm(text), norm(key_text), []
    for w in wrong or []:
        n = norm(w)
        if len(n) >= 2 and n not in k and re.search(r"(?<![\w])" + re.escape(n) + r"(?![\w])", t):
            hit.append(str(w))
    return hit


def check_voice(q, v, key_text, nscenes, src=None, wrong=None):
    """The owner's voice standard: stem, smart answer statement, short why, one thing to remember, at most 60 s.
    src (stem + key + explanation) and wrong (the wrong options' texts) add the accuracy checks: no number that the source
    does not have, no wrong option inside the answer statement."""
    import re
    if not isinstance(v, dict):
        return [f"{q}: missing voice"]
    err = [f"{q}: voice has an unknown field {k!r}" for k in sorted(set(v) - VOICE_KEYS)]
    qt = str(v.get("question", "")).strip()
    if not 1 <= len(qt) <= 220:
        err.append(f"{q}: voice question must be 1-220 characters (has {len(qt)})")
    at = str(v.get("answer", "")).strip()
    if not 1 <= len(at) <= 110:
        err.append(f"{q}: voice answer must be 1-110 characters (has {len(at)})")
    elif len(key_text) <= EXACT_MAX and norm(key_text) not in norm(at):
        err.append(f"{q}: the answer statement must contain the key's words exactly: {key_text}")
    if re.search(r"\b(option|answer)\s+[A-E]\b", at + " " + qt, re.I):
        err.append(f"{q}: never say option letters")
    tk = str(v.get("takeaway", "")).strip()
    if not 1 <= len(tk) <= 240:
        err.append(f"{q}: takeaway must be 1-240 characters (has {len(tk)})")
    ls = v.get("lines")
    if not isinstance(ls, list) or not 2 <= len(ls) <= 4:
        return err + [f"{q}: voice lines must be a list of 2-4 short explanation lines"]
    rem = v.get("remember")
    if not isinstance(rem, dict):
        return err + [f"{q}: remember must be one line object (text, scene, dir)"]
    if not str(rem.get("text", "")).strip().lower().startswith("remember"):
        err.append(f"{q}: the remember line must start with \"Remember\"")
    says = [str(v.get("question_say", "")), str(v.get("answer_say", ""))]
    for i, ln in enumerate(ls + [rem], 1):
        name = "remember line" if i == len(ls) + 1 else f"line {i}"
        if not isinstance(ln, dict):
            err.append(f"{q}: {name} must be an object")
            continue
        err += [f"{q}: {name} has an unknown field {k!r}" for k in sorted(set(ln) - LINE_KEYS)]
        t = str(ln.get("text", "")).strip()
        if not 1 <= len(t) <= 200:
            err.append(f"{q}: {name} text must be 1-200 characters")
        if re.search(r"\([a-z ]+\)", t.lower()) and any(x in t.lower() for x in EVENTS + ("(cough)",)):
            err.append(f"{q}: {name}: vocal events go in 'say' only, never in 'text'")
        sc = ln.get("scene")
        if not isinstance(sc, int) or isinstance(sc, bool) or not 0 <= sc <= nscenes:
            err.append(f"{q}: {name} scene must be a number 0-{nscenes} (0 = whole picture, 1 = first scene line ...)")
        d = str(ln.get("dir", "")).strip()
        if not 2 <= len(d.split()) <= 12:
            err.append(f"{q}: {name} needs a dir: a short delivery instruction of 2-12 words (tone, emotion, pace)")
        if re.search(r"\b(woman|man|female|male|girl|boy|accent|british|american|years? old)\b", d.lower()):
            err.append(f"{q}: {name} dir must not describe the voice itself (the voice is chosen automatically)")
        says.append(str(ln.get("say", "")))
    events = 0
    for sy in says:
        for ev in re.findall(r"\([a-z ]+\)", sy.lower()):
            if ev not in EVENTS:
                err.append(f"{q}: {ev} is not allowed; only (laugh), (sigh), (clears throat)")
        events += sum(sy.lower().count(x) for x in EVENTS)
    if events > 1:
        err.append(f"{q}: {events} vocal events; at most 1 per question")
    if src is not None:
        texts = [qt, at, tk] + [str(x.get("text", "")) for x in ls + [rem] if isinstance(x, dict)]
        extra = sorted(set().union(*(numbers_in(t) for t in texts)) - numbers_in(src))
        if extra:
            err.append(f"{q}: number(s) {', '.join(extra)} in the voice are not in the question, its answer or its explanation; "
                       "never invent numbers")
    bad = wrong_in(at, wrong, key_text)
    if bad:
        err.append(f"{q}: the answer statement contains a wrong option ({'; '.join(bad)}); say only the correct answer")
    secs = voice_seconds(v)
    if secs > MAX_SECONDS:
        err.append(f"{q}: the voice is about {secs} s; it must be at most {MAX_SECONDS} s: shorten the question part or the lines")
    return err


def voice_file(qids, items, EXPECT):
    """(file name, text) of one card's voice script. 'check' shows the Head whether a single character changed on the way."""
    import hashlib
    out = {"format": "kafu-voice-v1", "items": {}}
    for q in qids:
        it, v = items[q], items[q]["voice"]
        lesson = {"question": {"text": v["question"].strip()}, "answer": {"text": v["answer"].strip()},
                  "takeaway": v["takeaway"].strip(), "lines": []}
        for k in ("question", "answer"):
            if str(v.get(k + "_say", "")).strip():
                lesson[k]["say"] = v[k + "_say"].strip()
        for ln in list(v["lines"]) + [v["remember"]]:
            row = {"text": ln["text"].strip(), "scene": ln["scene"], "dir": ln["dir"].strip()}
            if str(ln.get("say", "")).strip():
                row["say"] = ln["say"].strip()
            lesson["lines"].append(row)
        out["items"][q] = {"n": EXPECT[q]["n"], "title": it["title"].strip(),
                           "scenes": [x.strip() for x in it["scenes"].splitlines() if x.strip()], "lesson": lesson}
    canon = _json.dumps(out, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    out["check"] = hashlib.sha256(canon.encode()).hexdigest()[:16]
    return f"VOICE_{qids[0]}-{qids[-1]}.txt", _json.dumps(out, indent=1, ensure_ascii=True)


def make_page(DATA, EXPECT, SETS, OUTNAME):
    import re
    err, standard = [], []
    items = DATA["items"]
    for q in items:
        if q not in EXPECT:
            err.append(f"{q}: not one of the questions of this batch")
    for q, e in EXPECT.items():
        it = items.get(q)
        if not it:
            err.append(f"{q} (question {e['n']}): missing")
            continue
        title, scenes, banner = (str(it.get(f, "")).strip() for f in ("title", "scenes", "banner"))
        if not title or len(title.split()) > 6:
            err.append(f"{q}: title must be 1-6 words")
        lines = [x for x in scenes.splitlines() if x.strip()]
        if not 3 <= len(lines) <= 5:
            err.append(f"{q}: scenes must be 3-5 lines, has {len(lines)}")
        labels = re.findall(r'"([^"]+)"', scenes)
        if not 3 <= len(labels) <= 12:
            err.append(f"{q}: 3-12 quoted labels needed, has {len(labels)}")
        for lab in labels:
            if len(lab.split()) > 5:
                err.append(f"{q}: label too long (max 5 words): {lab}")
        if "Answer" in scenes or "banner" in scenes.lower():
            err.append(f"{q}: put the answer only in 'banner', not in scenes")
        if not banner:
            err.append(f"{q}: empty banner")
        elif e["exact"] is not None and banner != e["exact"]:
            err.append(f"{q}: banner must be exactly: {e['exact']}")
        elif e["exact"] is None and len(banner.split()) > 10:
            err.append(f"{q}: banner longer than 10 words")
        if '"' in banner or '"' in title:
            err.append(f"{q}: no double quotes inside title or banner")
        ev = it.get("evidence")
        if not isinstance(ev, list) or len(ev) != len(lines):
            err.append(f"{q}: evidence needs {len(lines)} entries, one per scene line")
        else:
            qa, ex, key = norm(e["stem"] + " " + e["key"]), norm(e["expl"]), norm(e["key"])
            extra = 0
            for i, x in enumerate(ev, 1):
                x = str(x).strip()
                if x.upper().startswith("STANDARD:"):
                    extra += 1
                    if len(x) < 25:
                        err.append(f"{q}: scene {i}: write the standard reason after STANDARD:")
                    else:
                        standard.append(f"{q} (question {e['n']}) scene {i}: {x[9:].strip()}")
                elif key and norm(x) == key:
                    pass                                      # the correct answer itself
                elif len(x.split()) < 3:
                    err.append(f"{q}: scene {i}: evidence must quote 3 or more words (or the whole correct answer)")
                elif norm(x) in qa:
                    pass                                      # from the question or its correct answer
                elif norm(x) in ex:
                    extra += 1                                # from the book's explanation
                else:
                    err.append(f"{q}: scene {i}: this evidence is not in the stem, the correct answer or the explanation; "
                               f"copy it exactly (wrong options do not count): {x}")
            limit = max(1, round(0.3 * len(lines)))
            if extra > limit:
                err.append(f"{q}: {extra} of {len(lines)} scenes come from the explanation or your own knowledge; at most "
                           f"{limit}. The rest must show the question and its correct answer (evidence from the stem or the key)")
        allowed = e["stem"] + " " + e["key"] + " " + e["expl"]
        extra = sorted(numbers_in(" ".join(labels) + " " + title) - numbers_in(allowed))
        if extra:
            err.append(f"{q}: number(s) {', '.join(extra)} in the labels or title are not in the question, its answer or its "
                       "explanation; never invent numbers")
        bad = wrong_in(banner, e.get("wrong"), e["key"])
        if bad:
            err.append(f"{q}: the banner contains a wrong option ({'; '.join(bad)}); the banner shows only the correct answer")
        err += check_voice(q, it.get("voice"), e["key"], len(lines), allowed, e.get("wrong"))
    if err:
        print("ERROR - fix DATA and run again:")
        print("\n".join(err))
    else:
        cards = []
        for k, qids in enumerate(SETS):
            nums = ", ".join(EXPECT[q]["n"] for q in qids)
            vname, vtext = voice_file(qids, items, EXPECT)
            msg = [FRESH, "",
                   f'Go make {len(qids)} images, then save one text file: {len(qids) + 1} things in total, all in my Google Drive '
                   f'folder "{DRIVE_NAME}" ({DRIVE}).', "",
                   f"PART 1 - the {len(qids)} images. Work one image at a time, in this order:",
                   f"1. If <QID>.png is already in \"{DRIVE_NAME}\" now, skip that image.",
                   "2. Otherwise generate it from its prompt exactly as written (landscape 3:2, 1536x1024).",
                   "3. Check it: every quoted label present and spelled exactly; the bottom banner reads exactly as written; ONE story around ONE MAIN CHARACTER in the centre, every other character acting on it (Picmonic / Sketchy), no panels. If not, regenerate once.",
                   f"4. Save it to \"{DRIVE_NAME}\" in the same message, named exactly <QID>.png (capital Q, nine digits, .png, no other words). Then go on.",
                   "Do not stop after generating: generate, check, save, next. No drafts or duplicates in the folder; to replace an image, overwrite the same name.",
                   f"If you stop before the end and I write \"continue\", continue from the first image that is not yet in \"{DRIVE_NAME}\", then PART 2 if the text file is not there yet.",
                   f"When finished, reply with one line: images saved N/{len(qids)}, text file saved yes/no, and anything you could not save. "
                   "If you cannot save to Drive, say so plainly; never claim something was saved when it was not.",
                   ""]
            for i, q in enumerate(qids, 1):
                it = items[q]
                nz = len([x for x in it["scenes"].splitlines() if x.strip()])
                p = (f"Create a landscape 3:2 image (1536x1024). {STYLE}\n"
                     f"Layout: ONE single connected scene (no separate panels or zones): the {nz} story beats below all happen "
                     f"together around the MAIN CHARACTER; the title banner across the top, the answer banner across the bottom.\n"
                     f"Title banner at the top: \"{it['title'].strip()}\".\n"
                     f"{it['scenes'].strip()}\n"
                     f"Bottom banner: \"Answer --> {it['banner'].strip()}\".\n{AVOID}")
                msg += [f"===== IMAGE {i} of {len(qids)}: save as {q}.png (question {EXPECT[q]['n']}) =====", p, ""]
            msg += [f"PART 2 - the text file. After the images (even if one failed), save the text between the BEGIN and END lines "
                    f"to \"{DRIVE_NAME}\" as a plain text file named exactly {vname} (a .txt file, not a Google Doc). It is already "
                    "written: copy it character for character, do not fix, reformat, shorten or translate anything, and leave out the "
                    "BEGIN and END lines themselves. If a file with that name is already there, replace it.",
                    f"----- BEGIN {vname} -----", vtext, f"----- END {vname} -----"]
            cards.append((f"Card {k + 1}: questions {nums} ({len(qids)} images + {vname})", "\n".join(msg)))
        page = copy_page(OUTNAME[:-5], "Paste each card into a NEW ChatGPT chat (one card per chat). It draws the images and saves "
                         "them and one voice text file to Google Drive. Keep this file: it is also the backup of the voice text.", cards)
        open("/mnt/data/" + OUTNAME, "w", encoding="utf-8").write(page)
        print(f"OK - {len(EXPECT)} image prompts and {len(EXPECT)} voice scripts, {len(SETS)} card(s). File: /mnt/data/{OUTNAME}")
        for q in EXPECT:
            print(f"{q} (question {EXPECT[q]['n']}): voice about {voice_seconds(items[q]['voice'])} s")
        if standard:
            print("Tell the owner: these scenes use a standard reason because the book's explanation did not support the key:")
            print("\n".join(standard))
'''

# Per-chat script (questions inside the prompt): ChatGPT edits DATA only.
SCRIPT = r'''# ===== Kafu painter page builder. Edit ONLY the DATA block. Run it. Fix DATA until it prints OK. =====
DATA = {
  "items": {
    # one entry per QID. Example:
    # "Q000000001": {"title": """Oesophageal Hiatus""",
    #                "scenes": """LEFT: ... Label: "T10".
    # CENTER: ... Label: "Oesophagus".
    # RIGHT: ... labels "Anterior gastric nerve" and "Posterior gastric nerve".""",
    #                "banner": """T10""",
    #                "evidence": ["""corresponds to the level of T10""", """The oesophagus traverses""", """anterior and posterior gastric nerves"""],
    #                "voice": {"question": """...""", "answer": """...""", "lines": [{"text": """...""", "scene": 1, "dir": """..."""}],
    #                          "remember": {"text": """Remember: ...""", "scene": 0, "dir": """..."""}, "takeaway": """..."""}},
  },
}
# ===== do not change anything below this line =====
EXPECT = @@EXPECT@@
SETS = @@SETS@@
OUTNAME = "@@OUTNAME@@"
@@CORE@@
make_page(DATA, EXPECT, SETS, OUTNAME)
'''

# Master script (the owner attaches the app export to the chat): reads the export itself, batch by batch.
MASTER_SCRIPT = r'''# ===== Kafu master script: run this whole block once, exactly as it is =====
@@CORE@@
import glob as _glob, math as _math
BATCH_SIZE = @@BATCH@@
SET_SIZE = @@SET@@
EXACT_MAX = @@EXACT_MAX@@


def _int(v):
    s = str(v if v is not None else "")
    return (0, int(s), "") if s.isdigit() else (1, 0, s)


def _num(q):
    """Book, then chapter, then question number (9 before 10 before 101)."""
    return (str(q.get("book_id") or ""), _int(q.get("chapter_id")), _int(q.get("source_number")))


def _answer_text(q):
    opts, a = q.get("options", []), str(q.get("answer", "")).strip().upper()
    for i, o in enumerate(opts):
        lab = (o.get("label") or o.get("key") or o.get("letter") or "ABCDEFGH"[i]) if isinstance(o, dict) else "ABCDEFGH"[i]
        if str(lab).strip().upper() == a:
            return ((o.get("text") or o.get("value") or "") if isinstance(o, dict) else str(o)).strip()
    return ""


def _load(quiet=True):
    """Every app export attached to the chat: JSON files, or ZIP files that hold them (any number of files)."""
    import zipfile as _zip
    blobs = []
    for f in sorted(_glob.glob("/mnt/data/**/*", recursive=True)):
        if f.lower().endswith(".json"):
            blobs.append((f, open(f, "rb").read()))
        elif f.lower().endswith(".zip"):
            try:
                with _zip.ZipFile(f) as z:
                    blobs += [(f + ":" + n, z.read(n)) for n in z.namelist() if n.lower().endswith(".json")]
            except Exception:
                print(f"note: {f} is not a readable ZIP")
    found = []
    for name, b in blobs:
        try:
            d = _json.loads(b.decode("utf-8"))
        except Exception:
            continue
        if isinstance(d, dict) and d.get("export_type") == "kafu_mcq_text_export":
            found.append(d)
    if not found:
        raise SystemExit("NO EXPORT FOUND: ask the owner to upload the app export JSON files (or a ZIP of them) again.")
    qs = {}
    for d in found:
        for q in d.get("questions", []):
            qs.setdefault(q["id"], q)
    qs = sorted(qs.values(), key=_num)
    if not quiet:
        chap = {}
        for q in qs:
            k = (str(q.get("book_id") or ""), str(q.get("chapter_id") or ""))
            chap[k] = chap.get(k, 0) + 1
        print(f"{len(found)} export file(s), {len(qs)} questions, {_math.ceil(len(qs) / BATCH_SIZE)} batches of {BATCH_SIZE}:")
        for (b, c), n in sorted(chap.items(), key=lambda kv: (kv[0][0], _int(kv[0][1]))):
            print(f"  {b} chapter {c}: {n} questions")
    return qs


def show(n):
    """Prints batch n (1, 2, 3...) of the export: the questions to write prompts for."""
    global EXPECT, SETS, OUTNAME
    qs = _load()
    total = _math.ceil(len(qs) / BATCH_SIZE)
    chunk = qs[(n - 1) * BATCH_SIZE: n * BATCH_SIZE]
    if n < 1 or not chunk:
        print(f"NO BATCH {n}: the export has {len(qs)} questions = {total} batches.")
        EXPECT, SETS, OUTNAME = {}, [], ""
        return
    EXPECT, rows = {}, []
    for q in chunk:
        ans = _answer_text(q)
        if not ans:
            raise SystemExit(f"{q['id']}: the key {q.get('answer')!r} matches no option. Tell the owner; do not guess.")
        exact = ans if len(ans) <= EXACT_MAX and '"' not in ans else None
        opts = [(f"{o.get('label') or 'ABCDEFGH'[i]}. {(o.get('text') or o.get('value') or '').strip()}" if isinstance(o, dict)
                 else f"{'ABCDEFGH'[i]}. {str(o).strip()}") for i, o in enumerate(q.get("options", []))]
        letters = "ABCDEFGH"
        wrong = [((o.get("text") or o.get("value") or "") if isinstance(o, dict) else str(o)).strip()
                 for i, o in enumerate(q.get("options", []))
                 if str((o.get("label") or o.get("key") or o.get("letter") or letters[i]) if isinstance(o, dict) else letters[i]).strip().upper()
                 != str(q.get("answer", "")).strip().upper()]
        EXPECT[q["id"]] = {"n": str(q.get("source_number")), "exact": exact, "key": ans, "wrong": wrong,
                           "stem": q.get("stem", ""), "expl": q.get("explanation", "")}
        row = {"qid": q["id"], "question_number": q.get("source_number"), "stem": q.get("stem", ""), "options": opts,
               "key": q.get("answer"), "key_text": ans, "explanation": q.get("explanation", ""),
               "has_book_images": bool(q.get("images"))}
        if exact is not None:
            row["banner"] = exact
        rows.append(row)
    SETS = [[q["id"] for q in chunk[i:i + SET_SIZE]] for i in range(0, len(chunk), SET_SIZE)]
    first, last = chunk[0].get("source_number"), chunk[-1].get("source_number")
    chs = sorted({str(q.get("chapter_id")) for q in chunk}, key=_int)
    tag = "ch" + "+".join(chs)
    OUTNAME = f"painter_batch{n:02d}_{tag}_Q{first}-{last}.html"
    span = (f"questions {first}-{last}" if len(chs) == 1 else
            f"chapter {chunk[0].get('chapter_id')} question {first} to chapter {chunk[-1].get('chapter_id')} question {last}")
    print(f"BATCH {n} of {total}: chapter {', '.join(chs)}, {span}, {len(chunk)} questions, {len(SETS)} card(s): {SETS}")
    print(_json.dumps(rows, ensure_ascii=False, indent=1))


def make(DATA):
    """Checks DATA for the batch shown last and writes its painter file."""
    if not SETS:
        raise SystemExit("Run show(n) first.")
    make_page(DATA, EXPECT, SETS, OUTNAME)


SETS = []
try:
    _load(quiet=False)
except SystemExit as e:
    print(e)
print("Master script loaded. Next: show(<batch number>).")
'''

WRITER = '''You write image prompts and voice scripts for a medical-education app (Kafu). Do NOT draw any image and make
no audio in this chat.
Your only output is ONE downloadable HTML file, made by running the Python script at the end in your Python tool.

THE QUESTIONS ({N} multiple-choice questions, JSON below). The key is final: never change it, never contradict it.

STEP 1 - one picture plan per question, in Picmonic / Sketchy Medical style. Every fact becomes a SMART character or object:
a sound-alike or look-alike pun whose look, clothes or prop carries the fact (e.g. "T10" as a golfer's tee with a big 10, a
nerve as a yellow electric cable-man, an abscess as a walled castle full of pus-goblins). Each image has its own characters,
chosen for that question; they do not need to repeat across images. Characters act out the facts; nothing is decoration.
- "title": 2-5 words, the topic of the question.
- "scenes": 3-5 lines, one scene per line, left to right (start the lines with LEFT:, CENTER:, RIGHT: or similar). Each line
  says which character or object shows which fact and how, and ends with its label(s) in double quotes.
- "banner": the answer for the bottom banner (the script adds "Answer --> "). If the question lists an exact "banner", copy it
  character for character. Otherwise write the key's option text shortened faithfully to at most 8 words.
- WHAT THE IMAGE SHOWS (owner's rule): about 70% the question and its correct answer, about 30% the reason why. The reason
  comes from the book's explanation when possible; your own standard knowledge only when the explanation does not help.
  In numbers: with 3 or 4 scenes at most 1, with 5 scenes at most 2, may come from the explanation or your knowledge; all
  other scenes show what the stem asks and the correct answer. Never build a scene on a wrong option.
- "evidence": one entry per scene line, in the same order, proving the fact the scene shows:
  - from the question or the answer: an EXACT quote of 3 or more words from the stem, or the correct answer's text itself;
  - from the explanation: an EXACT quote of 3 or more words from the explanation;
  - from your own knowledge (only when the explanation is wrong or does not explain the key): "STANDARD: <the standard reason
    in one sentence>"; the script lists those for the owner to check.
  The script finds where each quote comes from and refuses a picture with too many explanation or knowledge scenes.
- "voice": the narration that plays under the picture in the app (see THE VOICE below).

THE VOICE (one narrated lesson per question, at most 60 seconds; the script estimates the length and refuses longer ones)
The engine is Breeze TTS 2 (open weights by BreezeBlue; we run Breeze-TTS-2.cpp, model breeze-tts-2-q8_0.gguf, English).
READ ONLY: you may read https://huggingface.co/BreezeBlue/Breeze-TTS-2 , https://raw.githubusercontent.com/HoppouAI/Breeze-TTS-2.cpp/main/README.md
and our pronunciation list https://raw.githubusercontent.com/blsmohamme972-lab/Mcqs-/master/voiceover/lexicon.json
to write lines that suit it. Never download, install or run the model or any audio tool, and make no audio. If a link does
not open, the facts below are enough:
- Each question gets one narrator, chosen automatically (6 designed voices: lecturer, doctor, student; women and men take
  turns). Never choose, name or describe a voice.
- "text" is what the screen shows; the voice reads "say" when there is one, otherwise "text". Use "say" only where the
  spoken form differs: numbers, units, abbreviations ("T10" -> "tee ten", "3 x 4 cm" -> "three by four centimetres"),
  a respelling listed under "say_breeze" in lexicon.json (e.g. proptosis -> "prop-TOE-sis"), or a vocal event.
- "dir" is the delivery instruction Breeze follows for that line (we send it as --instruction with --cfg-scale 4, so it is
  followed closely). Write it like the model card does: one short sentence about tone, emotion and pace, 2-12 words, e.g.
  "Speak clearly with gentle curiosity." / "Calm and confident, slightly slower." / "Warm and encouraging, a light smile."
  / "Firm and slow, stress the key words." Never describe the voice itself (no gender, age or accent).
- Vocal events go inside "say" in round brackets: only (laugh), (sigh) or (clears throat), at most one per question, only
  where it is natural (a light joke, a relief). Never (cough), never other tags.
- Write for the ear: short sentences, present tense, no symbols or arrows, never option letters ("C is correct"), a comma
  or colon for a natural pause. The voice speaks about 2.5 words per second.
The owner's structure, in this order:
1. "question" (on screen, max 220 characters, also read aloud): the stem. If it is long, only the important clinical
   points and the lead-in, e.g. "A 47-year-old man has a 3 by 4 cm abscess. Which statement about abscesses is correct?"
2. "answer" (on screen, max 110 characters, read aloud): THE MOST IMPORTANT PART. The correct answer as one smart, complete
   statement that contains the key's words, e.g. key "T10" -> "The oesophagus crosses the diaphragm at T10." Never a
   different answer, never weaker than the key.
3. "lines": 2-4 short lines that explain WHY, each pointing at a scene of the picture ("scene": 0 = whole picture,
   1 = first scene line, 2 = second ...). Facts only from the stem, key and explanation (the same rule as the evidence).
4. "remember": one last line that starts with "Remember", the one thing to keep for the exam, pointing at a scene.
5. "takeaway": the same key point as a short text for the end screen (max 240 characters).
Each of "lines" and "remember" is {"text": ..., "scene": n, "dir": ..., "say": ... (only if needed)}.
"question_say" and "answer_say" are optional spoken forms of the question and answer.

RULES (learned from earlier runs; they decide whether the images come out right):
- Facts only from the stem, the key and the explanation. Never invent numbers. If the explanation is wrong, contradictory or
  does not explain the key, show the short standard correct reason that supports the key.
- 3 to 12 quoted labels per question, 1 to 4 words each. A long list in one label comes out garbled: give each item its own
  short label, or show it with colour and no text. No double quotes except around labels.
- The picture is split into equal-width zones from left to right, one per scene line (3 lines = left, middle, right thirds),
  so the lesson camera can zoom on each scene. Every arrow or path must reach where the scene says.
- Never write a number (in labels, title, banner or voice) that is not in the stem, the key or the explanation: the script
  refuses it. Never let a wrong option appear in the banner or in the answer statement.
- Keep each character small enough (about a third of the width or less) to leave room for the other scenes.
- Never use the same object for two meanings within one image.
- The answer appears only on the banner, never inside the scenes.
- "has_book_images": true means the book shows a picture: describe only what the stem and explanation say.
- Nothing gory, no real photos, no brand names.
- Before you run the script, check every question once more: does each scene show a fact from its evidence, is the banner
  the key, is every label spelled as in the source, does the voice say only facts from the source, is the answer statement
  the key? Correct anything wrong first. Being right matters more than being fast.

STEP 2 - copy the script below exactly into your Python tool. Fill in only the DATA block (use triple quotes \"\"\" for
every text). Run it. If it prints ERROR, fix DATA and run it again until it prints OK. Then reply with only the download
link of the file {OUTNAME}. Never change the lines below "do not change anything below this line".

QUESTIONS:
{QUESTIONS}

SCRIPT:
```python
{SCRIPT}
```'''


def core():
    c = CORE
    for k, v in {"@@EXACT_MAX@@": str(EXACT_MAX), "@@DRIVE_NAME@@": CONFIG["drive_folder_name"], "@@DRIVE@@": CONFIG["drive_folder_url"], "@@STYLE@@": json.dumps(STYLE), "@@AVOID@@": json.dumps(AVOID),
                 "@@FRESH@@": json.dumps(FRESH.replace("@@DRIVE_NAME@@", CONFIG["drive_folder_name"])), "@@PAGE_CODE@@": PAGE_CODE.strip()}.items():
        c = c.replace(k, v)
    return c


# The fixed prompt for the owner who attaches the app export to the ChatGPT chat himself.
MASTER = """You write image prompts and voice scripts for a medical-education app (Kafu). Do NOT draw any image and make no
audio in this chat.
I attached my app export(s): one or many JSON files (export_type kafu_mcq_text_export), or ZIP files that hold them; the
master script reads them all, in order of book, chapter and question number. Their keys are final: never change or
contradict one.
You work in batches of @@BATCH@@ questions (@@NSETS@@ card(s) of up to @@SET@@ images). For each batch you give me one downloadable HTML
file, made by the master script below.

HOW TO WORK
1. Copy the master script below exactly into your Python tool and run it once (do not change any line of it). It prints how
   many export files, chapters, questions and batches it found: tell me that summary in one short message first.
2. Run show(1). It prints batch 1: its questions (stem, options, key, explanation, sometimes an exact "banner").
3. Write the DATA for that batch (STEP 1 below), then run make(DATA). If it prints ERROR, fix DATA and run
   make(DATA) again until it prints OK. Reply with only the download link of the file it names, plus one line:
   "batch n of N: questions a-b".
4. Then stop and wait. When I write "next", do the next batch the same way (show(2), then make(DATA), ...).
   When I write "next 3", do the next 3 batches one after another in the same reply (each: show, DATA, make, link).
   When I write "batch 5", do batch 5; "batches 5-8" does 5 to 8. When show() says there is no such batch, say all are done.
5. If Python was reset (NameError, or the file is gone), run the master script again; if it prints NO EXPORT FOUND,
   ask me to upload the export again.

DATA format (Python; use triple quotes \"\"\" for every text):
DATA = {"items": {"<QID>": {"title": \"\"\"...\"\"\", "scenes": \"\"\"LEFT: ... "Label".
CENTER: ... "Label".
RIGHT: ... "Label".\"\"\", "banner": \"\"\"...\"\"\",
                    "evidence": [\"\"\"exact quote for scene 1\"\"\", \"\"\"...scene 2\"\"\", \"\"\"...scene 3\"\"\"],
                    "voice": {"question": \"\"\"...\"\"\", "answer": \"\"\"...\"\"\",
                              "lines": [{"text": \"\"\"...\"\"\", "scene": 1, "dir": \"\"\"...\"\"\"}, ...2-4 lines],
                              "remember": {"text": \"\"\"Remember: ...\"\"\", "scene": 0, "dir": \"\"\"...\"\"\"},
                              "takeaway": \"\"\"...\"\"\"}}, ...one per QID of the batch}}

@@RULES@@

MASTER SCRIPT:
```python
@@MASTER_SCRIPT@@
```"""


def master_text():
    rules = WRITER[WRITER.index("STEP 1 - one picture plan"):WRITER.index("STEP 2 - copy")].strip()
    ms = MASTER_SCRIPT.replace("@@CORE@@", core())
    batch, set_size = CONFIG["gpt_writer_questions"], CONFIG["gpt_set_size"]
    for k, v in {"@@BATCH@@": str(batch), "@@SET@@": str(set_size), "@@EXACT_MAX@@": str(EXACT_MAX)}.items():
        ms = ms.replace(k, v)
    text = MASTER
    for k, v in {"@@BATCH@@": str(batch), "@@NSETS@@": str(-(-batch // set_size)), "@@SET@@": str(set_size),
                 "@@RULES@@": rules, "@@MASTER_SCRIPT@@": ms.strip()}.items():
        text = text.replace(k, v)
    assert "@@" not in text and "{N_SETS}" not in text
    return text, ms


def packages(prefix):
    out = [json.loads(p.read_text()) for p in QUEUE.glob(f"{prefix}-*.json")]
    return sorted(out, key=lambda q: [num_key(it.get("number")) for it in q["items"]])


def num_key(n):
    """Question numbers sort as numbers (9 before 10 before 101), anything else after them."""
    s = str(n)
    return (0, int(s), "") if s.isdigit() else (1, 0, s)


def wrong_options(it):
    """The texts of the options that are not the key (for the accuracy checks)."""
    letters, out = "ABCDEFGH", []
    for i, o in enumerate(it.get("options", [])):
        lab = (o.get("label") or o.get("key") or o.get("letter") or letters[i]) if isinstance(o, dict) else letters[i]
        if str(lab).strip().upper() != str(it.get("answer", "")).strip().upper():
            out.append(((o.get("text") or o.get("value") or "") if isinstance(o, dict) else str(o)).strip())
    return out


def letter_options(opts):
    res = []
    for i, o in enumerate(opts):
        if isinstance(o, dict):
            lab = (o.get("label") or o.get("key") or o.get("letter") or "ABCDEFGH"[i])
            res.append(f"{lab}. {(o.get('text') or o.get('value') or '').strip()}")
        else:
            res.append(f"{'ABCDEFGH'[i]}. {str(o).strip()}")
    return res


def build(prefix, per_chat, set_size, only=None):
    items = [it for q in packages(prefix) for it in q["items"]]
    if only:
        items = [it for it in items if it["qid"] in only]
    if not items:
        sys.exit(f"no questions for prefix {prefix} in {QUEUE}")
    seen = set()
    for it in items:
        if it["qid"] in seen:
            sys.exit(f"duplicate QID {it['qid']}")
        seen.add(it["qid"])
        if not it.get("answer_text", "").strip():
            sys.exit(f"{it['qid']}: no answer text (make_queue.py check)")
    cards = []
    for c in range(0, len(items), per_chat):
        chunk = items[c:c + per_chat]
        sets = [[it["qid"] for it in chunk[i:i + set_size]] for i in range(0, len(chunk), set_size)]
        first, last = chunk[0].get("number"), chunk[-1].get("number")
        outname = f"painter_{prefix}_Q{first}-{last}.html"
        expect = {}
        qs = []
        for it in chunk:
            ans = it["answer_text"].strip()
            exact = ans if len(ans) <= EXACT_MAX and '"' not in ans else None
            expect[it["qid"]] = {"n": str(it.get("number")), "exact": exact, "key": ans, "wrong": wrong_options(it),
                                 "stem": it.get("stem", ""), "expl": it.get("explanation", "")}
            row = {"qid": it["qid"], "question_number": it.get("number"), "stem": it.get("stem", ""),
                   "options": letter_options(it.get("options", [])), "key": it.get("answer"), "key_text": ans,
                   "explanation": it.get("explanation", ""), "has_book_images": bool(it.get("has_book_images"))}
            if exact is not None:
                row["banner"] = exact
            qs.append(row)
        script = SCRIPT.replace("@@CORE@@", core())
        for k, v in {"@@EXPECT@@": repr(expect), "@@SETS@@": repr(sets), "@@OUTNAME@@": outname}.items():
            script = script.replace(k, v)
        text = WRITER
        for k, v in {"{N}": str(len(chunk)), "{N_SETS}": str(len(sets)), "{SET}": str(set_size), "{OUTNAME}": outname,
                     "{QUESTIONS}": json.dumps(qs, ensure_ascii=False, indent=1), "{SCRIPT}": script.strip()}.items():
            text = text.replace(k, v)
        cards.append((f"Chat {len(cards) + 1}: questions {first}-{last} ({len(chunk)} questions, {len(sets)} sets of images)", text,
                      script, outname))
    return cards


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", help="per-chat mode: packages PREFIX-* from the queue (questions inside the prompts)")
    ap.add_argument("--master", action="store_true", help="the one fixed prompt; the owner attaches the export in ChatGPT")
    ap.add_argument("--out", required=True)
    ap.add_argument("--per-chat", type=int, default=CONFIG["gpt_writer_questions"])
    ap.add_argument("--set", type=int, default=CONFIG["gpt_set_size"])
    ap.add_argument("--qids", help="only these QIDs, comma separated (e.g. to redo a few)")
    ap.add_argument("--dump-scripts", help="folder: also save each chat's script (for testing)")
    a = ap.parse_args()
    ns = {}
    exec(PAGE_CODE, ns)
    if a.master:
        text, ms = master_text()
        Path(a.out).write_text(ns["copy_page"](
            "Kafu: ChatGPT master prompt",
            "Open a NEW ChatGPT chat, attach the app export (JSON), press Copy, paste, send. ChatGPT gives one painter_batchNN "
            "file per batch; write next for the next batch. Open each painter file in Chrome: each card goes into a NEW chat.",
            [("Master prompt (attach the export JSON to the same message)", text)]), encoding="utf-8")
        if a.dump_scripts:
            Path(a.dump_scripts).mkdir(parents=True, exist_ok=True)
            (Path(a.dump_scripts) / "master.py").write_text(ms)
        print(f"{a.out}: master prompt, {len(text)} chars")
        return
    if not a.prefix:
        sys.exit("--prefix or --master")
    cards = build(a.prefix, a.per_chat, a.set, set(a.qids.split(",")) if a.qids else None)
    page = ns["copy_page"](f"Kafu {a.prefix}: ChatGPT writer prompts",
                           "Step 1. Paste each card into a NEW ChatGPT chat. ChatGPT gives you a painter_...html file: open it in "
                           "Chrome and paste each of its cards into a NEW chat (step 2), which draws and saves the images.",
                           [(h, t) for h, t, _, _ in cards])
    Path(a.out).write_text(page, encoding="utf-8")
    if a.dump_scripts:
        d = Path(a.dump_scripts)
        d.mkdir(parents=True, exist_ok=True)
        for i, (_, _, s, o) in enumerate(cards, 1):
            (d / f"chat{i:02d}.py").write_text(s)
    n = sum(t.count('"qid":') for _, t, _, _ in cards)
    print(f"{a.out}: {len(cards)} writer chats, {n} questions, longest card {max(len(t) for _, t, _, _ in cards)} chars")


if __name__ == "__main__":
    main()
