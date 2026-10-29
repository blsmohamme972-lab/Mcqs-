#!/usr/bin/env python3
"""One master prompt for ChatGPT: the owner attaches the app export, ChatGPT WRITES the image prompts (the job the Head
did for questions 1-100) batch by batch and gives one painter HTML file per batch, in the same format as before
(head_prompts.py page: think first, real Iraqi place as a cartoon background, one connected scene, save <QID>.png to
Drive, then a places_*.txt notes file).

  python3 gpt_master_prompts.py --from 101 --to 200 --out master_Q101-200.html [--test-dir DIR]

The master script inside the prompt is self-contained (json/html/re/glob/math only). --test-dir runs it here on a
folder that holds the export (instead of /mnt/data) so it can be tested before the owner uses it.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gpt_writer as g  # noqa: E402
import head_prompts as hp  # noqa: E402
from kafu_data import CONFIG  # noqa: E402

MASTER_SCRIPT = r'''# ===== Kafu image-prompt master script: run this whole block once, exactly as it is =====
import json as _json, glob as _glob, math as _math, re as _re, html as _html
DATA_DIR = "@@DATA_DIR@@"
Q_FROM, Q_TO = @@FROM@@, @@TO@@
BATCH_SIZE = @@BATCH@@
EXACT_MAX = 60
DRIVE = @@DRIVE@@
DRIVE_NAME = @@DRIVE_NAME@@
STYLE = @@STYLE@@
AVOID = @@AVOID@@
HOW = @@HOW@@
FRESH = @@FRESH@@
@@PAGE_CODE@@

def _int(v):
    s = str(v if v is not None else "").strip()
    return int(s) if s.isdigit() else None

def _opt(o, i):
    if isinstance(o, dict):
        return (str(o.get("label") or o.get("key") or o.get("letter") or "ABCDEFGH"[i]).strip().upper(),
                str(o.get("text") or o.get("value") or "").strip())
    return "ABCDEFGH"[i], str(o).strip()

def _load(quiet=True):
    import zipfile as _zip
    blobs = []
    for f in sorted(_glob.glob(DATA_DIR + "/**/*", recursive=True)):
        if f.lower().endswith(".json"):
            blobs.append(open(f, "rb").read())
        elif f.lower().endswith(".zip"):
            try:
                with _zip.ZipFile(f) as z:
                    blobs += [z.read(n) for n in z.namelist() if n.lower().endswith(".json")]
            except Exception:
                print("note: " + f + " is not a readable ZIP")
    qs = {}
    for b in blobs:
        try:
            d = _json.loads(b.decode("utf-8"))
        except Exception:
            continue
        if isinstance(d, dict) and d.get("export_type") == "kafu_mcq_text_export":
            for q in d.get("questions", []):
                qs.setdefault(q["id"], q)
    if not qs:
        raise SystemExit("NO EXPORT FOUND: ask the owner to upload the app export JSON (or a ZIP of it) again.")
    sel = [q for q in qs.values() if _int(q.get("source_number")) is not None and Q_FROM <= _int(q.get("source_number")) <= Q_TO]
    sel.sort(key=lambda q: _int(q.get("source_number")))
    nums = [_int(q.get("source_number")) for q in sel]
    if len(set(nums)) != len(nums):
        raise SystemExit("The export holds the same question number twice (more than one chapter?). Tell the owner; do not guess.")
    if not quiet:
        missing = [n for n in range(Q_FROM, Q_TO + 1) if n not in nums]
        print(f"{len(qs)} questions in the export; questions {Q_FROM}-{Q_TO}: {len(sel)} found"
              + (f", missing numbers: {missing}" if missing else "") + f"; {_math.ceil(len(sel) / BATCH_SIZE)} batches of {BATCH_SIZE}.")
    return sel

def norm(t):
    t = str(t).lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    t = t.replace("–", "-").replace("—", "-")
    return _re.sub(r"\s+", " ", _re.sub(r"[^\w%'\-./ ]+", " ", t)).strip()

def numbers_in(t):
    return set(_re.findall(r"\d+(?:\.\d+)?", str(t)))

def wrong_in(text, wrong, key_text):
    t, k, hit = norm(text), norm(key_text), []
    for w in wrong or []:
        n = norm(w)
        if len(n) >= 2 and n not in k and _re.search(r"(?<![\w])" + _re.escape(n) + r"(?![\w])", t):
            hit.append(str(w))
    return hit

EXPECT, ORDER, OUTNAME = {}, [], ""

def show(n):
    """Prints batch n (1, 2, 3...): the questions to write image prompts for."""
    global EXPECT, ORDER, OUTNAME
    qs = _load()
    total = _math.ceil(len(qs) / BATCH_SIZE)
    chunk = qs[(n - 1) * BATCH_SIZE: n * BATCH_SIZE]
    if n < 1 or not chunk:
        print(f"NO BATCH {n}: questions {Q_FROM}-{Q_TO} make {total} batches. All done.")
        EXPECT, ORDER, OUTNAME = {}, [], ""
        return
    EXPECT, ORDER, rows = {}, [], []
    for q in chunk:
        opts = [_opt(o, i) for i, o in enumerate(q.get("options", []))]
        key = str(q.get("answer", "")).strip().upper()
        ans = [t for l, t in opts if l == key]
        if not ans or not ans[0]:
            raise SystemExit(f"{q['id']}: the key {q.get('answer')!r} matches no option. Tell the owner; do not guess.")
        ans = ans[0]
        exact = ans if len(ans) <= EXACT_MAX and '"' not in ans else None
        EXPECT[q["id"]] = {"n": str(q.get("source_number")), "exact": exact, "key": ans,
                           "wrong": [t for l, t in opts if l != key], "stem": q.get("stem", ""), "expl": q.get("explanation", "")}
        ORDER.append(q["id"])
        row = {"qid": q["id"], "question_number": q.get("source_number"), "stem": q.get("stem", ""),
               "options": [f"{l}. {t}" for l, t in opts], "key": key, "key_text": ans,
               "explanation": q.get("explanation", ""), "has_book_images": bool(q.get("images"))}
        if exact is not None:
            row["banner"] = exact
        rows.append(row)
    first, last = chunk[0].get("source_number"), chunk[-1].get("source_number")
    OUTNAME = f"painter_Q{first}-{last}.html"
    print(f"BATCH {n} of {total}: questions {first}-{last}, {len(chunk)} questions. Write DATA for these QIDs: {ORDER}")
    print(_json.dumps(rows, ensure_ascii=False, indent=1))

def make(DATA):
    """Checks DATA for the batch shown last and writes its painter file."""
    if not EXPECT:
        raise SystemExit("Run show(n) first.")
    err, standard = [], []
    for q in DATA:
        if q not in EXPECT:
            err.append(f"{q}: not one of the questions of this batch")
    for q in ORDER:
        e, it = EXPECT[q], DATA.get(q)
        if not it:
            err.append(f"{q} (question {e['n']}): missing")
            continue
        title, place = str(it.get("title", "")).strip(), str(it.get("place", "")).strip()
        banner = str(it.get("banner") or "").strip()
        chars = it.get("characters") or []
        if not title or len(title.split()) > 6:
            err.append(f"{q}: title must be 1-6 words")
        if not place:
            err.append(f"{q}: place is missing")
        if not 3 <= len(chars) <= 5:
            err.append(f"{q}: 3-5 characters needed, has {len(chars)}")
        texts = [str(c.get("text", "")).strip() if isinstance(c, dict) else "" for c in chars]
        if texts and "MAIN CHARACTER" not in texts[0]:
            err.append(f"{q}: the first character line must start with 'the MAIN CHARACTER:'")
        labels = _re.findall(r'"([^"]+)"', " ".join(texts))
        if not 3 <= len(labels) <= 12:
            err.append(f"{q}: 3-12 quoted labels needed, has {len(labels)}")
        for lab in labels:
            if len(lab.split()) > 5:
                err.append(f"{q}: label too long (max 5 words): {lab}")
        for t in texts:
            if not _re.search(r'"[^"]+"', t):
                err.append(f"{q}: every character line needs its label(s) in double quotes: {t[:60]}")
        if "Answer" in " ".join(texts):
            err.append(f"{q}: the answer goes only on the banner, not in the characters")
        if e["exact"] is not None:
            if banner and banner != e["exact"]:
                err.append(f"{q}: banner must be exactly the key: {e['exact']} (or leave it empty)")
            banner = e["exact"]
        elif not banner:
            err.append(f"{q}: the key is long: write a faithful short banner (max 10 words)")
        elif len(banner.split()) > 10:
            err.append(f"{q}: banner longer than 10 words")
        if '"' in banner or '"' in title:
            err.append(f"{q}: no double quotes inside title or banner")
        bad = wrong_in(banner, e["wrong"], e["key"])
        if bad:
            err.append(f"{q}: the banner contains a wrong option ({'; '.join(bad)})")
        qa, ex, key = norm(e["stem"] + " " + e["key"]), norm(e["expl"]), norm(e["key"])
        extra = 0
        for i, c in enumerate(chars, 1):
            x = str(c.get("evidence", "") if isinstance(c, dict) else "").strip()
            if x.upper().startswith("STANDARD:"):
                extra += 1
                if len(x) < 25:
                    err.append(f"{q}: character {i}: write the standard reason after STANDARD:")
                else:
                    standard.append(f"{q} (question {e['n']}) character {i}: {x[9:].strip()}")
            elif key and norm(x) == key:
                pass
            elif len(x.split()) < 3:
                err.append(f"{q}: character {i}: evidence must quote 3 or more words (or the whole correct answer)")
            elif norm(x) in qa:
                pass
            elif norm(x) in ex:
                extra += 1
            else:
                err.append(f"{q}: character {i}: this evidence is not in the stem, the correct answer or the explanation; "
                           f"copy it exactly (wrong options do not count): {x}")
        limit = max(1, round(0.3 * len(chars)))
        if extra > limit:
            err.append(f"{q}: {extra} of {len(chars)} characters come from the explanation or your own knowledge; at most {limit}")
        allowed = e["stem"] + " " + e["key"] + " " + e["expl"]
        newnum = sorted(numbers_in(" ".join(labels) + " " + title) - numbers_in(allowed))
        if newnum:
            err.append(f"{q}: number(s) {', '.join(newnum)} in labels or title are not in the question, answer or explanation")
        it["_banner"] = banner
    if err:
        print("ERROR - fix DATA and run make(DATA) again:")
        print("\n".join(err))
        return
    ch = ORDER
    msg = [FRESH, "", f'Go make {len(ch)} images, all saved in my Google Drive folder "{DRIVE_NAME}" ({DRIVE}).', "", HOW,
           "ORDER OF WORK, one image at a time:",
           f'1. If <QID>.png is already in "{DRIVE_NAME}" now, skip that image.',
           "2. Otherwise think (A), then generate it (one image, 3:2, 1536x1024).",
           "3. Check it: every quoted label present and spelled exactly; the bottom banner reads exactly as written; ONE story around ONE MAIN CHARACTER in the centre, every other character acting on it (Picmonic / Sketchy), no panels. If not, regenerate once.",
           f'4. Save it to "{DRIVE_NAME}" in the same message, named exactly <QID>.png (capital Q, nine digits, .png, no other words). Then go on.',
           "Do not stop after generating: think, generate, check, save, next. No drafts or duplicates in the folder; to replace an image, overwrite the same name.",
           f'If you stop before the end and I write "continue", continue from the first image that is not yet in "{DRIVE_NAME}".',
           f"After the last image (even if one failed) do PART 2 below. When finished, reply with one line: images saved N/{len(ch)}, places file saved yes/no, and anything you could not save. If you cannot save to Drive, say so plainly; never claim something was saved when it was not.", ""]
    for i, q in enumerate(ch, 1):
        it, e = DATA[q], EXPECT[q]
        names = ["MAIN CHARACTER"] + [f"CHARACTER {k + 2}" for k in range(len(it["characters"]) - 1)]
        scenes = "\n".join(f"{nm}: {_re.sub(r'^(the )?MAIN CHARACTER:\s*', '', str(c['text']).strip(), flags=_re.I)}"
                           for nm, c in zip(names, it["characters"]))
        note = str(e["expl"]).replace("\n", " ").strip()[:420]
        p = (f"QUESTION: {str(e['stem']).strip()}\nCORRECT ANSWER: {e['key']}\nBOOK NOTE (source for the optional 25 percent extra): {note}\n"
             f"Create ONE landscape 3:2 image (1536x1024). {STYLE}\n"
             f"Layout: ONE single connected scene (no separate panels). Title banner across the top, answer banner across the bottom.\n"
             f"Place (familiar, Iraqi flavour no more than 10 percent): {str(it['place']).strip()}.\n"
             f"Title banner at the top: \"{str(it['title']).strip()}\".\n"
             f"Story brief (improve it, keep the labels exactly):\n{scenes}\n"
             f"Bottom banner: \"Answer --> {it['_banner']}\".\n{AVOID}")
        msg += [f"===== IMAGE {i} of {len(ch)}: save as {q}.png (question {e['n']}) =====", p, ""]
    pname = f"places_{ch[0]}-{ch[-1]}.txt"
    msg += [f'PART 2 - the places notes file. After the images, write ONE plain text file named exactly {pname} (a .txt file, not a Google Doc) and save it to "{DRIVE_NAME}". For each image, in the same order, write 4 to 7 short lines: the QID and question number; the real place you chose (its name and city) and what the cartoon background looks like; the MAIN CHARACTER and what it stands for; each other character with the single fact it stands for; the funny idea, pun or memory trick; and any extra fact you added beyond the question and correct answer (say it is extra). Keep it plain and short: these notes help the voice-over writer know exactly what the picture shows. If a file with that name is already there, replace it.', ""]
    nums = ", ".join(EXPECT[q]["n"] for q in ch)
    page = copy_page(OUTNAME[:-5], "Paste the card into a NEW ChatGPT chat. It thinks, looks up the real places, draws one connected "
                     "story image per question, saves each to Google Drive as <QID>.png, then saves one places_*.txt notes file.",
                     [(f"Card: questions {nums} ({len(ch)} images)", "\n".join(msg))])
    open(DATA_DIR + "/" + OUTNAME, "w", encoding="utf-8").write(page)
    print(f"OK - {len(ch)} image prompts. File: {DATA_DIR}/{OUTNAME}")
    if standard:
        print("Tell the owner: these characters use a standard reason because the book's explanation did not support the key:")
        print("\n".join(standard))

try:
    _load(quiet=False)
except SystemExit as _e:
    print(_e)
print("Master script loaded. Next: show(1).")
'''

PROMPT = '''You write IMAGE PROMPTS for a medical-education app (Kafu). Do NOT draw any image in this chat.
I attached my app export (JSON, export_type kafu_mcq_text_export) of one book chapter. You do questions @@FROM@@ to @@TO@@
of it, in batches of @@BATCH@@. For each batch you give me ONE downloadable HTML file (a painter page) made by the master
script below. Its keys are final: never change or contradict a key.

HOW TO WORK
1. Copy the master script below exactly into your Python tool and run it once (do not change any line). It prints how many
   questions it found: tell me that summary in one short line first, then go straight on with batch 1.
2. Run show(1). It prints batch 1: stem, options, key, explanation (sometimes an exact "banner").
3. Write DATA for that batch (THE BRIEF below), then run make(DATA). If it prints ERROR, fix DATA and run make(DATA) again
   until it prints OK. Reply with the download link of the file it names, plus one line: "batch n of N: questions a-b",
   plus the STANDARD lines it printed, if any.
4. Then stop and wait. "next" = the next batch the same way. "next 3" = the next 3 batches one after another in the same
   reply (each: show, DATA, make, link). "batch 5" = batch 5. When show() says there is no such batch, say all are done.
5. If Python was reset (NameError, or the file is gone), run the master script again; if it prints NO EXPORT FOUND, ask me
   to upload the export again.

DATA format (Python; use triple quotes \"\"\" for every text):
DATA = {"<QID>": {"title": \"\"\"...\"\"\", "banner": \"\"\"\"\"\" , "place": \"\"\"...\"\"\",
                  "characters": [{"text": \"\"\"the MAIN CHARACTER: ... labelled "Label".\"\"\", "evidence": \"\"\"exact quote\"\"\"},
                                 {"text": \"\"\"... labelled "Label".\"\"\", "evidence": \"\"\"exact quote\"\"\"}, ...3 to 5]},
        ...one entry per QID of the batch}

THE BRIEF (per question; this is exactly how the owner's earlier 100 prompts were written)
- "title": 2-5 words, a catchy story title for the topic, e.g. "Telescope Tummy", "Breathing Away the Acid".
- "banner": leave it empty ("") when the question shows an exact "banner" (the script uses the key itself). Otherwise write
  the key's option text shortened faithfully to at most 8 words. Never a wrong option, never weaker than the key.
- "place": a real, familiar place in Iraq where the scene happens. About 30 percent of the questions: a real Iraqi
  hospital, e.g. "Baghdad Teaching Hospital, Baghdad Medical City (Bab Al-Moatham, Baghdad)", "Children's Welfare Teaching
  Hospital, Baghdad Medical City, Baghdad", "Al-Kindy Teaching Hospital, Baghdad", "Al-Yarmouk Teaching Hospital emergency
  department, Baghdad", "Ibn Al-Nafees Hospital (vascular and cardiac), Baghdad", "Al-Sayyab Teaching Hospital, Basra".
  The rest: everyday Iraqi places (Al-Mutanabbi Street, a riverside cafe on Abu Nuwas Street, a Basra date-palm grove, a
  Mosul old-city bakery, a Kurdistan mountain road, a university campus...). Pick one that fits the story; vary them.
- "characters": 3 to 5 lines. Line 1 starts with "the MAIN CHARACTER:" (the patient, the organ, the molecule or the hero of
  the question). Every other character acts on the main character and carries exactly ONE fact. Picmonic / Sketchy style:
  every fact becomes a smart, funny character or object (a sound-alike or look-alike pun whose look, clothes or prop carries
  the fact). Each line ends with its label(s) in double quotes, e.g. labelled "8 months" and "Vomiting".
- "evidence" (one per character): proof of the fact that character shows:
  - from the question or the answer: an EXACT quote of 3 or more words from the stem, or the correct answer's text itself;
  - from the explanation: an EXACT quote of 3 or more words from the explanation;
  - from your own knowledge (only when the explanation is wrong or does not explain the key): "STANDARD: <the standard
    reason in one sentence>".
  At most 1 character (with 3-4 characters) or 2 (with 5) may come from the explanation or your knowledge; all the others
  show what the stem asks and its correct answer. Never build a character on a wrong option.

RULES (learned from earlier runs)
- Facts only from the stem, the key and the explanation. Never invent numbers: a number in a label or the title must be in
  the stem, the key or the explanation (the script refuses others). If the explanation is wrong or does not explain the
  key, use the short standard correct reason that supports the key.
- 3 to 12 quoted labels per question, 1 to 5 words each; a long list in one label comes out garbled: give each item its
  own short label. No double quotes except around labels.
- The answer appears only on the banner, never in the characters.
- "has_book_images": true means the book shows a picture: describe only what the stem and explanation say.
- Nothing gory, no real photos of people, no brand names, no flags, no religious figures, no real people.
- Before make(DATA), check every question once more: does each character show a fact from its evidence, is the banner the
  key, is every label spelled as in the source? Being right matters more than being fast.

MASTER SCRIPT:
```python
@@MASTER_SCRIPT@@
```'''


def build(q_from, q_to, data_dir="/mnt/data"):
    batch = CONFIG["gpt_set_size"]
    ms = MASTER_SCRIPT
    rep = {"@@DATA_DIR@@": data_dir, "@@FROM@@": str(q_from), "@@TO@@": str(q_to), "@@BATCH@@": str(batch),
           "@@DRIVE@@": json.dumps(CONFIG["drive_folder_url"]), "@@DRIVE_NAME@@": json.dumps(CONFIG["drive_folder_name"]),
           "@@STYLE@@": json.dumps(hp.STYLE), "@@AVOID@@": json.dumps(hp.AVOID), "@@HOW@@": json.dumps(hp.HOW),
           "@@FRESH@@": json.dumps(g.FRESH.replace("@@DRIVE_NAME@@", CONFIG["drive_folder_name"])),
           "@@PAGE_CODE@@": g.PAGE_CODE.strip()}
    for k, v in rep.items():
        ms = ms.replace(k, v)
    assert g.STORY_RULES in hp.STYLE, "every image prompt must carry the story rules (they travel in STYLE)"
    text = PROMPT
    for k, v in {"@@FROM@@": str(q_from), "@@TO@@": str(q_to), "@@BATCH@@": str(batch), "@@MASTER_SCRIPT@@": ms.strip()}.items():
        text = text.replace(k, v)
    assert "@@" not in text and "@@" not in ms
    return text, ms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="q_from", type=int, required=True)
    ap.add_argument("--to", dest="q_to", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--test-dir")
    a = ap.parse_args()
    text, _ = build(a.q_from, a.q_to)
    ns = {}
    exec(g.PAGE_CODE, ns)
    Path(a.out).write_text(ns["copy_page"](
        f"Kafu: ChatGPT image-prompt master, questions {a.q_from}-{a.q_to}",
        "Open a NEW ChatGPT chat, attach the app export (JSON) to the same message, press Copy, paste, send. ChatGPT writes "
        "the image prompts and gives one painter_Q...html file per batch of 8; write next for the next batch. Open each "
        "painter file in Chrome: its card goes into a NEW chat, which draws and saves the images.",
        [(f"Master prompt, questions {a.q_from}-{a.q_to} (attach the export JSON to the same message)", text)]), encoding="utf-8")
    print(f"{a.out}: {len(text)} chars")
    if a.test_dir:
        _, ms = build(a.q_from, a.q_to, a.test_dir)
        Path(a.test_dir, "master.py").write_text(ms)


if __name__ == "__main__":
    main()
