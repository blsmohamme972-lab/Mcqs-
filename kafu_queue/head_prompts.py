#!/usr/bin/env python3
"""The Head writes every image prompt itself (owner's workflow since 2026-10-16); ChatGPT only thinks, draws and saves.

  head_prompts.py check FILE            check the Head's prompt file against the queue packages (the same rules as the
                                        old ChatGPT writer: every QID once, banner = the key's text, no wrong option on
                                        the banner, evidence per character line, no invented numbers, 3-5 lines)
  head_prompts.py page FILE OUT.html    check, then write the painter page: one card per 8 images for a NEW ChatGPT
                                        chat each; ChatGPT thinks first, uses a real photo of the place as a cartoon
                                        background, draws ONE connected story per question, saves <QID>.png to Drive
                                        and then one places_<first>-<last>.txt notes file per card (places_collect.py)

FILE (in the run's data folder, e.g. <data>/prompts/BAILEY-CH1_Q101-200.json):
  {"prefix": "BAILEY-CH1", "items": [{"qid": "Q000000133", "title": "...", "banner": null (= the key's text) or a short
   form for a key longer than 60 characters, "place": "a familiar Iraqi place (about 30 percent real Iraqi hospitals)",
   "characters": [{"text": "line 1 = the MAIN CHARACTER ... Label: \"...\".", "evidence": "words copied from the stem,
   the key or the explanation"}, ... 3 to 5 lines, every other character acts on the main character]}]}
A key the Head corrected (key_corrected in the package item) is used as the key; the banner shows the corrected answer.
"""
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gpt_writer as g  # noqa: E402
from kafu_data import CONFIG, QUEUE  # noqa: E402

STYLE=("Picmonic and Sketchy-style visual mnemonic for medical students: cute, funny, expressive cartoon characters with big friendly eyes, "
       "bright flat colours, thick dark outlines, rich storytelling detail. All text sits in rounded white label boxes with dark navy bold letters, "
       "crisp and spelled exactly as given. " + g.STORY_RULES)
AVOID=("Avoid: garbled or misspelled text, extra text that is not in quotes here, duplicated characters, distorted faces, photographs, "
       "watermarks, cluttered dark background, and anything real-person-like.")
HOW=("HOW TO WORK ON EVERY IMAGE BELOW (read once, apply to each image)\n"
"A. THINK FIRST, BRIEFLY, before drawing each image (no need to show long reasoning; if you can search the web, take a quick look at how Picmonic and Sketchy "
"teach this topic): (1) How can these characters be made better, funnier and more expressive? (2) How can the story be more connected, so that ONE scene "
"tells everything? (3) What will make it stick in memory: visual puns, sound-alikes, exaggeration, emotion, a tiny joke that makes a student smile? "
"Improve the brief below with your own best ideas, but keep every label and the bottom banner exactly as written.\n"
"B. ONE connected scene, not separate panels: one MAIN CHARACTER (the patient, the organ, the molecule or the hero of the question) stands in the middle of "
"the whole picture; every other character is close to the main character, touches it, helps it, attacks it or reacts to it, and each secondary character "
"carries exactly one fact. Everything happens together in one place and one moment, like a Picmonic story.\n"
"C. FOCUS on the question and its correct answer: about 75 percent of the story must show the question and the correct answer. If something is very important, "
"you may add up to about 25 percent extra information from the BOOK NOTE given with the image, or from your own accurate medical knowledge, to make the "
"picture exact, exciting and unforgettable. Never contradict the correct answer, never put a wrong option in the picture as if it were true, and never invent "
"numbers that the question does not give.\n"
"D. BELONGING: the scene happens in the familiar place named in each brief, a real everyday place that a student in Iraq knows. Bring the Picmonic fantasy "
"(imagine it was brought in from America or Europe) INTO that familiar place, so it feels like home and makes the student smile or laugh. The Iraqi flavour "
"is a light touch, no more than about 10 percent of the whole picture (a few places, props, tea glasses, palm trees, clothes). The rest is the medical "
"story. THE BACKGROUND: first search for real photos of that famous place in Baghdad or Iraq (or the closest famous place if the named one is generic), choose one good photo as the background, and turn it into a cartoon or caricature drawing of that place (use the photo only as a reference and redraw it, do not paste a photograph). Then build the story scene on top of that background with fitting shapes and characters. If you cannot search or use photos, draw the place from your own knowledge of how it really looks. Put most of your effort into the characters and into accuracy of every label. ABOUT 30 PERCENT of the images are set in real hospitals or health places in Iraq (named in the brief) so that students remember them with the medical setting: look up how those hospitals and wards really look. Be respectful: no religious figures, no real people, no flags, no insulting stereotypes. Make the caricature characters funny but kind. If a character line mentions a setting that does not fit the named place (for example a clinic bed), the named place wins: move the action into that place.\n"
"E. IMAGE POLICY: if anything in a brief (blood, wounds, surgery, genitals, injuries, very sensitive scenes) would break your image rules, quietly change it so it is "
"allowed (for example a red cartoon splash instead of blood, a covered or symbolic version, a toy-like organ, a speech bubble instead of a graphic scene) while "
"keeping the same medical meaning and the same labels. Do not refuse; adapt and still make the image. Never put real gore in the picture.\n"
"F. Landscape 3:2, 1536x1024. Text only in the quoted labels, the title banner at the top and the bottom banner, spelled exactly as given.\n")

def load(path):
    spec = json.loads(Path(path).read_text())
    items = {it["qid"]: it for p in g.packages(spec["prefix"]) for it in p["items"]}
    ns = {}
    core = (g.CORE.replace("@@EXACT_MAX@@", str(g.EXACT_MAX)).replace("@@DRIVE@@", CONFIG["drive_folder_url"])
            .replace("@@DRIVE_NAME@@", CONFIG["drive_folder_name"]).replace("@@STYLE@@", repr(g.STYLE))
            .replace("@@AVOID@@", repr(g.AVOID)).replace("@@FRESH@@", repr(g.FRESH)).replace("@@PAGE_CODE@@", g.PAGE_CODE))
    exec(core, ns)
    ns["check_voice"] = lambda *a, **k: []             # no voice here: the builder sessions write it
    data, expect, err = {"items": {}}, {}, []
    seen = set()
    for row in spec["items"]:
        q = row["qid"]
        if q in seen:
            err.append(f"{q}: twice in the file")
        seen.add(q)
        it = items.get(q)
        if not it:
            err.append(f"{q}: not in any {spec['prefix']}-* package")
            continue
        ans = it["answer_text"].strip()
        exact = ans if len(ans) <= g.EXACT_MAX and '"' not in ans else None
        expect[q] = {"n": str(it["number"]), "exact": exact, "key": ans, "wrong": g.wrong_options(it),
                     "stem": it.get("stem", ""), "expl": it.get("explanation", ""), "corrected": bool(it.get("key_corrected"))}
        chars = row["characters"]
        names = ["MAIN CHARACTER"] + [f"CHARACTER {i + 2}" for i in range(len(chars) - 1)]
        data["items"][q] = {"title": row["title"], "place": row.get("place", "").strip(),
                            "scenes": "\n".join(f"{nm}: {c['text']}" for nm, c in zip(names, chars)),
                            "banner": row.get("banner") or ans, "evidence": [c["evidence"] for c in chars]}
        if not data["items"][q]["place"]:
            err.append(f"{q}: no place")
    out = io.StringIO()
    old = sys.stdout
    sys.stdout = out
    try:
        ns["make_page"](data, expect, [], "unused.html") if not err else None
    except (KeyError, FileNotFoundError, OSError):
        pass                                           # make_page's own page writing / voice summary: not used here
    finally:
        sys.stdout = old
    text = out.getvalue()
    if "ERROR" in text:
        err += [x for x in text.splitlines()[1:] if x.strip()]
    return spec, data["items"], expect, err


def page(path, outpath):
    spec, D, E, err = load(path)
    if err:
        sys.exit("ERROR - fix the prompt file:\n" + "\n".join(err))
    DRIVE, NAME = CONFIG["drive_folder_url"], CONFIG["drive_folder_name"]
    ns = {}
    exec(g.PAGE_CODE, ns)
    FRESH = g.FRESH.replace("@@DRIVE_NAME@@", NAME)
    qids=list(E); cards=[]
    for k in range(0,len(qids),8):
        ch=qids[k:k+8]
        msg=[FRESH,"",f'Go make {len(ch)} images, all saved in my Google Drive folder "{NAME}" ({DRIVE}).',"",HOW,
         "ORDER OF WORK, one image at a time:",
         f'1. If <QID>.png is already in "{NAME}" now, skip that image.',
         "2. Otherwise think (A), then generate it (one image, 3:2, 1536x1024).",
         "3. Check it: every quoted label present and spelled exactly; the bottom banner reads exactly as written; ONE story around ONE MAIN CHARACTER in the centre, every other character acting on it (Picmonic / Sketchy), no panels. If not, regenerate once.",
         f'4. Save it to "{NAME}" in the same message, named exactly <QID>.png (capital Q, nine digits, .png, no other words). Then go on.',
         "Do not stop after generating: think, generate, check, save, next. No drafts or duplicates in the folder; to replace an image, overwrite the same name.",
         f'If you stop before the end and I write "continue", continue from the first image that is not yet in "{NAME}".',
         f"After the last image (even if one failed) do PART 2 below. When finished, reply with one line: images saved N/{len(ch)}, places file saved yes/no, and anything you could not save. If you cannot save to Drive, say so plainly; never claim something was saved when it was not.",""]
        for i,q in enumerate(ch,1):
            it=D[q]; e=E[q]
            note=e["expl"].replace("\n"," ").strip()[:420]
            p=(f"QUESTION: {e['stem'].strip()}\nCORRECT ANSWER: {e['key'].strip()}\nBOOK NOTE (source for the optional 25 percent extra): {note}\n"
               f"Create ONE landscape 3:2 image (1536x1024). {STYLE}\n"
               f"Layout: ONE single connected scene (no separate panels). Title banner across the top, answer banner across the bottom.\n"
               f"Place (familiar, Iraqi flavour no more than 10 percent): {it['place']}.\n"
               f"Title banner at the top: \"{it['title'].strip()}\".\n"
               f"Story brief (improve it, keep the labels exactly):\n{it['scenes'].strip()}\n"
               f"Bottom banner: \"Answer --> {it['banner'].strip()}\".\n{AVOID}")
            assert g.STORY_RULES in p, "every image prompt must carry the story rules"
            msg+=[f"===== IMAGE {i} of {len(ch)}: save as {q}.png (question {e['n']}) =====",p,""]
        pname=f"places_{ch[0]}-{ch[-1]}.txt"
        msg+=[f'PART 2 - the places notes file. After the images, write ONE plain text file named exactly {pname} (a .txt file, not a Google Doc) and save it to "{NAME}". For each image, in the same order, write 4 to 7 short lines: the QID and question number; the real place you chose (its name and city) and what the cartoon background looks like; the MAIN CHARACTER and what it stands for; each other character with the single fact it stands for; the funny idea, pun or memory trick; and any extra fact you added beyond the question and correct answer (say it is extra). Keep it plain and short: these notes help the voice-over writer know exactly what the picture shows. If a file with that name is already there, replace it.',""]
        nums=", ".join(E[q]["n"] for q in ch)
        cards.append((f"Card {k//8+1}: questions {nums} ({len(ch)} images)","\n".join(msg)))

    page = ns["copy_page"](Path(outpath).stem, "Paste each card into a NEW ChatGPT chat (one card per chat). ChatGPT thinks, looks "
                           "up the real places, draws one connected story image per question, saves it to Google Drive as "
                           "<QID>.png, then saves one short places_*.txt notes file per card. The builder sessions use the notes "
                           "to write the voice (places_collect.py adds them to the packages).", cards)
    Path(outpath).write_text(page, encoding="utf-8")
    fixed = [q for q in E if E[q]["corrected"]]
    print(f"{outpath}: {len(E)} images in {len(cards)} cards, longest card {max(len(t) for _, t in cards)} chars"
          + (f"; corrected keys: {', '.join(fixed)}" if fixed else ""))


def main(a):
    if len(a) >= 2 and a[0] == "check":
        _, _, E, err = load(a[1])
        if err:
            sys.exit("ERROR - fix the prompt file:\n" + "\n".join(err))
        print(f"OK: {len(E)} prompts")
    elif len(a) >= 3 and a[0] == "page":
        page(a[1], a[2])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
