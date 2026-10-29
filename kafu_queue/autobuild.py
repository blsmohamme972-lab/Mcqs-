#!/usr/bin/env python3
"""Build a builder session's whole share of packages in ONE background job (builder sessions).

  setsid nohup python3 /home/user/kq/kafu_queue/autobuild.py run --packages P1,P2,... > work/autobuild.out 2>&1 < /dev/null &
        (detached on purpose: a tool's background command is stopped after at most 2 hours; options --images-dir DIR,
        --max-hours 16)
  python3 /home/user/kq/kafu_queue/autobuild.py status
  python3 /home/user/kq/kafu_queue/autobuild.py uploaded PKG [PKG ...]
  python3 /home/user/kq/kafu_queue/autobuild.py retry PKG

Run it from the root of the Mcqs- checkout, after bundle.py unpack. `run` needs no Claude turn between steps:
  1. the exports are copied to work/input/ and checked (preflight.py export);
  2. the voice engine is set up and tested (voice_setup.py: robust download + 4-second Breeze clip);
  3. it loops over the packages: a package starts as soon as all its images are in the Drive folder and every question has
     a checked voice script (from the bundle, or read from the VOICE_*.txt files in Drive as they appear). Then:
     scaffold -> images -> lesson files (lesson_from_voice.py) -> Breeze voice + scenes -> lint -> package -> validate ->
     size check -> base64 for the inbox. One package at a time (one Breeze job), so the CPU never waits for the session.
     A failed step is retried once; the second failure is reported and the next package goes on.
  4. it waits for missing images (polling Drive every 2 minutes, no tokens used) up to --max-hours.
The session only uploads what `status` lists under UPLOAD (Artifact publish), marks it with `uploaded`, and answers the rare
WRITE_LESSONS / FAILED lines. State lives in work/autobuild/ (never committed); `run` again resumes where it stopped.
"""
import argparse
import base64
import io
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kafu_data as K  # noqa: E402
import watch  # noqa: E402

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
VPY = Path.home() / ".venvs" / "kafu-voice" / "bin" / "python"
REPO = Path.cwd()
ST = REPO / "work" / "autobuild"
STATE = ST / "state.json"
VOICE_GRACE_MIN = 30          # images complete but a voice script still missing this long: ask the session to write it
TERMINAL = ("ready", "send", "failed")


# ---------------- state (written by `run` only; the session's commands leave marker files) ----------------
def load():
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save(st):
    ST.mkdir(parents=True, exist_ok=True)
    st["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=1))
    os.replace(tmp, STATE)


def marked(kind, pkg):
    return (ST / kind / pkg).exists()


def mark(kind, pkg):
    (ST / kind).mkdir(parents=True, exist_ok=True)
    (ST / kind / pkg).write_text(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


def alive(pid):
    """True when that process exists and is an autobuild run (a reused pid of another program does not count)."""
    try:
        return b"autobuild.py" in Path(f"/proc/{int(pid)}/cmdline").read_bytes()
    except (OSError, ValueError, TypeError):
        return False


def env():
    return {**os.environ, "MOTIONCARDS_CHROMIUM": CHROME, "KAFU_MOUNTAIN": str(REPO)}


def sh(cmd, log, py=None):
    """Run one step; its output goes to the package log. Returns (exit code, last lines)."""
    with open(log, "a") as f:
        f.write(f"\n$ {' '.join(map(str, cmd))}\n")
        f.flush()
        r = subprocess.run([str(c) for c in cmd], cwd=REPO, env=env(), stdout=f, stderr=subprocess.STDOUT)
    tail = Path(log).read_text(errors="replace").strip().splitlines()[-15:]
    return r.returncode, tail


# ---------------- readiness ----------------
def drive_images():
    every = []
    watch.list_drive(watch.CONFIG["drive_folder_id"], every=every)
    out = {}
    for name, fid in every:
        if len(name) == 14 and name.startswith("Q") and name.endswith(".png"):
            out.setdefault(name[:10], fid)
    return out


def have_images(qids, imgs, images_dir):
    if images_dir:
        return [q for q in qids if (Path(images_dir) / f"{q}.png").exists()]
    return [q for q in qids if q in imgs]


def refresh_voice(items, missing):
    """Read VOICE_*.txt from Drive for the QIDs still without a voice script; keep the ones that pass every check."""
    import voice_collect
    srcs, _ = voice_collect.drive_sources(set(missing))
    good, problems = voice_collect.verify(srcs, {q: items[q] for q in missing})
    K.VOICE.mkdir(parents=True, exist_ok=True)
    for q, row in good.items():
        (K.VOICE / f"{q}.json").write_text(json.dumps(row, indent=1, ensure_ascii=False) + "\n")
    return problems


# ---------------- one package ----------------
def build(pkg, q, imgs, images_dir, log):
    """Every step for one package. Returns (state, note, files)."""
    from PIL import Image
    W = REPO / "work" / pkg
    E = REPO / "work" / "input" / Path(q["export"]).name
    Z = REPO / "dist" / f"MCARDS_{pkg}_r1.zip"
    qids = [it["qid"] for it in q["items"]]
    shutil.rmtree(W, ignore_errors=True)
    (REPO / "dist").mkdir(exist_ok=True)
    for old in (REPO / "dist").glob(f"MCARDS_{pkg}_r1*"):
        old.unlink()
    cmd = ["python3", "tools/motioncards.py", "scaffold", E, "--out", W, "--package-id", pkg, "--revision", "1",
           "--qids", *qids, "--duration-ms", "30000"]
    for it in q["items"]:
        if q.get("already_live"):
            cmd += ["--replace", it["qid"]]
        if it.get("has_book_images"):
            if not it.get("book_images_inspected"):        # never bypass the project's gate: the Head must have looked
                return "final", (f"{it['qid']} has book images that nobody has looked at yet: the Head looks at them, runs "
                                 f"make_queue.py inspected {it['qid']}, packs a new bundle"), []
            cmd += ["--inspected-image-qid", it["qid"]]
    code, tail = sh(cmd, log)
    if code:
        return "error", "scaffold: " + " | ".join(tail[-3:]), []
    (W / "lessons").mkdir(parents=True, exist_ok=True)
    warn = []
    for qid in qids:                                   # the images, saved the way watch.py get saves them
        if images_dir:
            im = Image.open(Path(images_dir) / f"{qid}.png")
        else:
            im = Image.open(io.BytesIO(watch.download(imgs[qid])))
        im.load()
        im.convert("RGB").save(W / "lessons" / f"{qid}.png")
        if watch.image_warning(im):
            warn.append(f"{qid} {im.size[0]}x{im.size[1]}")
    for qid in qids:                                   # lessons the session wrote for questions without a voice script
        own = ST / "lessons" / f"{qid}.lesson.json"
        if own.exists():
            shutil.copy(own, W / "lessons" / own.name)
    code, tail = sh(["python3", HERE / "lesson_from_voice.py", W / "lessons", *qids], log)
    if code:
        return "error", "lesson files: " + " | ".join(tail[-3:]), []
    missing = [qid for qid in qids if not (W / "lessons" / f"{qid}.lesson.json").exists()]
    if missing:
        return "error", "no lesson file for " + " ".join(missing), []
    code, tail = sh([VPY, "tools/motioncards.py", "lesson", "--workspace", W], log)
    if code:
        return "error", "voice build: " + " | ".join(tail[-3:]), []
    recog = "word timing without the recogniser" in Path(log).read_text(errors="replace")
    for step in (["python3", "tools/motioncards.py", "lint", "--workspace", W],
                 ["python3", "tools/motioncards.py", "package", E, "--workspace", W, "--out", Z]):
        code, tail = sh(step, log)
        if code:
            return "error", f"{step[2]}: " + " | ".join(tail[-3:]), []
    zips = sorted((REPO / "dist").glob(f"MCARDS_{pkg}_r1*.zip"))
    if not zips:
        return "error", "package made no ZIP", []
    files, big = [], False
    for z in zips:
        code, tail = sh(["python3", "tools/motioncards.py", "validate", z], log)
        if code:
            return "error", "validate: " + " | ".join(tail[-3:]), []
        if z.stat().st_size > K.CONFIG["max_package_zip_mb"] * 1024 * 1024:
            big = True
        b64 = z.with_name(z.name + ".b64.txt")
        b64.write_bytes(base64.b64encode(z.read_bytes()))
        files.append({"zip": str(z), "b64": str(b64), "bytes": z.stat().st_size})
    note = []
    if warn:
        note.append("image size warning: " + ", ".join(warn))
    if recog:
        note.append("word timing without the recogniser")
    return ("send" if big else "ready"), "; ".join(note), files


# ---------------- the loop ----------------
def run(a):
    st = load()
    if st.get("pid") and alive(st["pid"]) and st["pid"] != os.getpid():
        sys.exit(f"autobuild is already running (pid {st['pid']})")
    pk = watch.packages()
    pkgs = a.packages.split(",") if a.packages else st.get("args", {}).get("packages", [])
    if not pkgs:
        sys.exit("no packages: give --packages P1,P2,...")
    unknown = [p for p in pkgs if p not in pk]
    if unknown:
        sys.exit(f"unknown packages (not in the bundle): {unknown}")
    images_dir = a.images_dir or st.get("args", {}).get("images_dir")
    st.pop("finished", None)
    st.update(pid=os.getpid(), args={"packages": pkgs, "images_dir": images_dir, "max_hours": a.max_hours},
              started=st.get("started") or time.time())
    st.setdefault("pkgs", {p: {"state": "waiting", "tries": 0, "note": ""} for p in pkgs})
    for p in pkgs:
        st["pkgs"].setdefault(p, {"state": "waiting", "tries": 0, "note": ""})
        if st["pkgs"][p]["state"] == "building":          # interrupted mid-build: build it again
            st["pkgs"][p]["state"] = "waiting"
    save(st)
    print(f"autobuild: {len(pkgs)} packages, repo {REPO}, data {K.DATA}", flush=True)

    # 1. exports
    (REPO / "work" / "input").mkdir(parents=True, exist_ok=True)
    for name in sorted({Path(pk[p]["export"]).name for p in pkgs}):
        shutil.copy(K.export_path(name), REPO / "work" / "input" / name)
        r = subprocess.run(["python3", HERE / "preflight.py", "export", REPO / "work" / "input" / name],
                           cwd=REPO, env=env(), capture_output=True, text=True)
        if "PREFLIGHT export OK" not in r.stdout:
            st["export"] = "rejected: " + (r.stdout + r.stderr).strip().splitlines()[-2:][0][:300]
            save(st)
            sys.exit("EXPORT REJECTED")
    st["export"] = "ok"
    save(st)

    # 2. voice engine (KAFU_TEST_NO_VOICE=1 skips it: only for testing the loop without Breeze)
    if os.environ.get("KAFU_TEST_NO_VOICE"):
        st["voice"] = "skipped (test)"
        save(st)
    if st.get("voice") not in ("ok", "skipped (test)"):
        st["voice"] = "setting up"
        save(st)
        r = subprocess.run(["python3", HERE / "voice_setup.py", REPO], cwd=REPO, env=env(), capture_output=True, text=True)
        (ST / "voice_setup.log").write_text(r.stdout + r.stderr)
        last = (r.stdout.strip().splitlines() or ["no output"])[-1]
        st["voice"] = "ok" if r.returncode == 0 else "broken: " + last[:300]
        save(st)
        if r.returncode:
            sys.exit("VOICE BROKEN")

    # 3. packages
    deadline = st["started"] + a.max_hours * 3600
    while True:
        st = load()
        st["pid"] = os.getpid()
        for p in pkgs:                                    # the session asked for a retry
            if marked("retry", p):
                (ST / "retry" / p).unlink()
                st["pkgs"][p].update(state="waiting", tries=0, note="retry asked", retry_after=0)
        todo = [p for p in pkgs if st["pkgs"][p]["state"] not in TERMINAL]
        if not todo:
            break
        try:
            imgs = {} if images_dir else drive_images()
        except Exception as e:  # noqa: BLE001  (a network blip must not stop the build: try again next round)
            print(f"Drive listing failed ({type(e).__name__}); trying again in {a.poll} s", flush=True)
            if time.time() > deadline:
                for p in todo:
                    st["pkgs"][p].update(state="failed", note=f"Drive folder unreachable ({type(e).__name__}) until the time limit")
                save(st)
                break
            time.sleep(a.poll)
            continue
        built = False
        for p in todo:
            if st["pkgs"][p].get("retry_after", 0) > time.time():
                continue
            q = pk[p]
            items = {it["qid"]: it for it in q["items"]}
            qids = list(items)
            got = have_images(qids, imgs, images_dir)
            novoice = [x for x in qids if not (K.VOICE / f"{x}.json").exists() and not (ST / "lessons" / f"{x}.lesson.json").exists()]
            if novoice and len(got) == len(qids):
                try:
                    problems = refresh_voice(items, novoice)
                except Exception as e:  # noqa: BLE001
                    problems = [f"reading voice files from Drive failed ({type(e).__name__}); trying again"]
                novoice = [x for x in novoice if not (K.VOICE / f"{x}.json").exists()]
                if problems:
                    st["pkgs"][p]["voice_problems"] = problems[-3:]
            row = st["pkgs"][p]
            row["images"], row["voice"] = f"{len(got)}/{len(qids)}", f"{len(qids) - len(novoice)}/{len(qids)}"
            if len(got) < len(qids):
                row.update(state="waiting", since=None)
                continue
            if novoice:
                row.setdefault("since", None)
                row["since"] = row["since"] or time.time()
                if time.time() - row["since"] > a.voice_grace_min * 60:
                    row.update(state="needs_lessons", need=novoice)
                    (ST / "preview").mkdir(parents=True, exist_ok=True)
                    for x in novoice:                     # images for the session to look at while writing
                        dst = ST / "preview" / f"{x}.png"
                        if not dst.exists():
                            src = Path(images_dir) / f"{x}.png" if images_dir else None
                            data = src.read_bytes() if src else watch.download(imgs[x])
                            dst.write_bytes(data)
                else:
                    row["state"] = "waiting"
                continue
            row.update(state="building", started=time.time())
            save(st)
            log = ST / f"{p}.log"
            t0 = time.time()
            try:
                state, note, files = build(p, q, imgs, images_dir, log)
            except Exception as e:  # noqa: BLE001
                state, note, files = "error", f"{type(e).__name__}: {e}", []
            row["secs"] = round(time.time() - t0)
            if state == "final":
                row.update(state="failed", note=note)
            elif state == "error":
                row["tries"] = row.get("tries", 0) + 1
                row.update(state="failed" if row["tries"] >= 2 else "waiting", note=note,
                           retry_after=time.time() + 300)       # a passing cause (network, download) gets 5 minutes
            else:
                row.update(state=state, note=note, files=files, done=time.time())
            print(f"{p}: {row['state']} in {row['secs']} s {note}", flush=True)
            save(st)
            built = True
            break                                         # re-read Drive and markers after every package
        save(st)
        if not built:
            if time.time() > deadline:
                for p in pkgs:
                    if st["pkgs"][p]["state"] not in TERMINAL:
                        st["pkgs"][p].update(state="failed", note=f"gave up waiting after {a.max_hours} h")
                save(st)
                break
            time.sleep(a.poll)
    st = load()
    st["finished"] = time.time()
    save(st)
    print("autobuild finished", flush=True)


def status(a):
    st = load()
    if not st:
        print("autobuild has not started (no work/autobuild/state.json)")
        return
    running = alive(st.get("pid")) and not st.get("finished")
    pk = st.get("pkgs", {})
    counts = {}
    for p, row in pk.items():
        s = "uploaded" if marked("uploaded", p) else row["state"]
        counts[s] = counts.get(s, 0) + 1
    print(f"autobuild: {'RUNNING' if running else ('FINISHED' if st.get('finished') else 'STOPPED (run it again)')} | "
          f"export {st.get('export', '-')} | voice {st.get('voice', '-')} | "
          + " ".join(f"{k} {v}" for k, v in sorted(counts.items())) + f" | total {len(pk)}")
    done = [r for r in pk.values() if r.get("secs") and r["state"] in ("ready", "send")]
    if done:
        nq = sum(int(r["images"].split("/")[1]) for r in done)
        print(f"speed: {sum(r['secs'] for r in done) / max(1, nq) / 60:.1f} min per question over {len(done)} package(s)")
    for p, row in pk.items():
        if marked("uploaded", p):
            continue
        s = row["state"]
        if s == "ready":
            for f in row.get("files", []):
                print(f"UPLOAD {p} {f['b64']} ({f['bytes']} bytes){(' note: ' + row['note']) if row.get('note') else ''}")
        elif s == "send":
            for f in row.get("files", []):
                print(f"SEND_TO_OWNER {p} {f['zip']} ({f['bytes']} bytes, over {K.CONFIG['max_package_zip_mb']} MB)")
        elif s == "needs_lessons":
            print(f"WRITE_LESSONS {p} {' '.join(row.get('need', []))}: write work/autobuild/lessons/<QID>.lesson.json "
                  "(owner's voice standard; look at work/autobuild/preview/<QID>.png)" +
                  (f"; voice file problems: {row['voice_problems']}" if row.get("voice_problems") else ""))
        elif s == "failed":
            print(f"FAILED {p}: {row.get('note', '')} (log work/autobuild/{p}.log)")
        elif s == "building":
            print(f"BUILDING {p} for {round((time.time() - row.get('started', time.time())) / 60)} min")
        elif s == "waiting":
            print(f"WAITING {p}: images {row.get('images', '?')}, voice scripts {row.get('voice', '?')}"
                  + (f", retry after: {row['note']}" if row.get("tries") else ""))
    if st.get("finished") and all(marked("uploaded", p) or r["state"] == "failed" for p, r in pk.items()):
        print("ALL DONE")


def main():
    global REPO, ST, STATE
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--packages")
    r.add_argument("--images-dir")
    r.add_argument("--max-hours", type=float, default=16)
    r.add_argument("--poll", type=int, default=120)
    r.add_argument("--voice-grace-min", type=float, default=VOICE_GRACE_MIN,
                   help="images complete but a voice script still missing this long: WRITE_LESSONS")
    sub.add_parser("status")
    u = sub.add_parser("uploaded")
    u.add_argument("pkgs", nargs="+")
    t = sub.add_parser("retry")
    t.add_argument("pkg")
    a = ap.parse_args()
    if not (REPO / "tools" / "motioncards.py").exists():
        sys.exit("run this from the root of the Mcqs- checkout")
    if a.cmd == "run":
        run(a)
    elif a.cmd == "status":
        status(a)
    elif a.cmd == "uploaded":
        for p in a.pkgs:
            mark("uploaded", p)
        status(a)
    elif a.cmd == "retry":
        mark("retry", a.pkg)
        print(f"{a.pkg}: will be built again on the next loop")


if __name__ == "__main__":
    main()
