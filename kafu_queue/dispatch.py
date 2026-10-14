#!/usr/bin/env python3
"""Head Department dispatcher for the 30 warm builders.

Every run: read the Drive images, find the chapter-36 packages whose images are all there, and give each newly
ready package to the slot that has the fewest packages so far (ties: lowest slot number). Already assigned
packages never move. Packages that are not ready yet are not in any slot (the pool). Commits and pushes
assignments.json only when it changed.

  dispatch.py once      one pass
  dispatch.py loop N    a pass every N seconds (default 300)
Slots listed in dead_slots.txt (one number per line, optional) get nothing new.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import watch  # noqa: E402

AF = HERE / "assignments.json"
DEAD = HERE / "dead_slots.txt"
PREFIX = "GT-CH36-"


def run_once():
    a = json.loads(AF.read_text())
    slots = a["slots"]
    rows, imgs = watch.progress()
    ready = [r[0] for r in rows if r[0].startswith(PREFIX) and r[1] == r[2]]
    allpk = [r[0] for r in rows if r[0].startswith(PREFIX)]
    dead = {f"{int(x):02d}" for x in DEAD.read_text().split()} if DEAD.exists() else set()
    changed = []
    for s in slots:                      # drop packages that are no longer ready (an image was removed)
        keep = [p for p in slots[s] if p in ready]
        if keep != slots[s]:
            changed.append(f"UNREADY {set(slots[s]) - set(keep)} from {s}")
            slots[s] = keep
    led = watch.ledger()
    done = {k for k, v in led.items() if v.get("state") == "delivered"}
    assigned = {p for v in slots.values() for p in v}
    for p in sorted(ready, key=lambda x: allpk.index(x)):
        if p in assigned:
            continue
        live = [s for s in sorted(slots) if s not in dead]
        s = min(live, key=lambda k: (len([x for x in slots[k] if x not in done]), k))
        slots[s].append(p)
        changed.append(f"ASSIGN {p} -> {s}")
    total_img = sum(r[1] for r in rows if r[0].startswith(PREFIX))
    total_q = sum(r[2] for r in rows if r[0].startswith(PREFIX))
    if changed:
        AF.write_text(json.dumps(a, indent=1) + "\n")
        subprocess.run(["git", "-C", str(HERE.parent), "add", "kafu_queue/assignments.json"], check=True)
        subprocess.run(["git", "-C", str(HERE.parent), "commit", "-q", "-m",
                        f"Dispatch: {len(ready)} packages ready\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\n"
                        "Claude-Session: https://claude.ai/code/session_012LgVug8ba6ZtxNC2QsGMQq"], check=True)
        r = subprocess.run(["git", "-C", str(HERE.parent), "push", "-q", "origin", "HEAD"], capture_output=True, text=True)
        if r.returncode:
            print("PUSH FAILED", r.stderr.strip()[:300], flush=True)
    for c in changed:
        print(c, flush=True)
    load = sorted(len(v) for v in slots.values())
    print(f"STATE images {total_img}/{total_q} ready_packages {len(ready)}/{len(allpk)} max_load {load[-1]} min_load {load[0]}", flush=True)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "once"
    if mode == "loop":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 300
        while True:
            try:
                run_once()
            except Exception as e:   # keep the loop alive
                print("ERROR", repr(e)[:300], flush=True)
            time.sleep(n)
    else:
        run_once()
