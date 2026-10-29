#!/usr/bin/env python3
"""Fixed work split for the builder sessions (Head Department). Builders start only after preflight.py images is OK,
so every package is known in advance and nothing has to be dispatched while they run.

  assign.py split PREFIX N [--from Q]  assignments.json: the packages PREFIX-* in question order, cut into N slots (N = the
                                    number of builder sessions the OWNER chose) with nearly equal question counts, each slot
                                    a run of neighbouring packages. Refuses to overwrite a split that already has deliveries.
  assign.py prompt SLOT --bundle ID the full first message for that slot's builder session (BUILDER.md filled in);
                                    ID = the inbox asset id of the run's bundle (bundle.py pack, then upload it)
  assign.py prompt SLOT --bundle ID --packages P1,P2 [--as NN]
                                    the same for a replacement session: only these packages, under slot name NN
  assign.py resize PREFIX N [--from Q]  repack the undelivered packages PREFIX-* into exactly N packages of nearly equal size
                                    (sizes differ by at most one question), so that N sessions each get ONE package and
                                    finish together. Run it after the owner picks N and before split. Keeps every item field
                                    (key_corrected, picture_notes). --from Q: only packages whose first question number is >= Q (this
                                    run). Refuses if a chosen package is already building or delivered.
  assign.py left                    per slot: packages not yet delivered in the ledger (what a replacement must do)
  assign.py options PREFIX [--from Q]  the owner's choice table: for several session counts, the time to build everything
                                    once the images exist, and the estimated money per builder model (config.json numbers)
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import watch  # noqa: E402

from kafu_data import ASSIGN as AF, export_path  # noqa: E402
CONFIG = watch.CONFIG


def plan(names, sizes, n):
    """Consecutive packages per slot, balanced by question count (the same split for 'split' and 'options')."""
    total = sum(sizes)
    n = max(1, min(n, len(names)))
    slots, cur, acc, k = {}, [], 0, 1
    for i, (p, s) in enumerate(zip(names, sizes)):
        cur.append(p)
        acc += s
        left_pk, left_slots = len(names) - i - 1, n - k
        if k < n and (acc >= total * k / n or left_pk == left_slots):
            slots[f"{k:02d}"], cur, k = cur, [], k + 1
    if cur:
        slots[f"{k:02d}"] = cur
    return slots


def split(prefix, n, qmin=None):
    from kafu_data import require_data_folder
    require_data_folder()
    pk = {k: v for k, v in watch.packages().items() if k.startswith(prefix + "-")}
    if qmin is not None:                               # a new run on the same prefix: only its questions
        pk = {k: v for k, v in pk.items() if str(v["items"][0].get("number")).isdigit()
              and int(v["items"][0]["number"]) >= qmin}
    if not pk:
        sys.exit(f"no packages {prefix}-*")
    if AF.exists():
        old = json.loads(AF.read_text())
        led = watch.ledger()
        if any(led.get(p, {}).get("state") == "delivered" for v in old["slots"].values() for p in v):
            if qmin is None or set(p for v in old["slots"].values() for p in v) & set(pk):
                sys.exit("assignments.json already has delivered packages; use 'left' and 'prompt --packages' instead "
                         "(a NEW run on the same prefix: split PREFIX N --from <its first question number>)")
            keep = AF.with_name(f"assignments.before_Q{qmin}.json")
            AF.rename(keep)
            print(f"previous run's split kept as {keep.name}")
    names = list(pk)
    sizes = [len(pk[p]["items"]) for p in names]
    total = sum(sizes)
    if n > len(names):
        print(f"note: {n} sessions asked but only {len(names)} packages: using {len(names)}")
    slots = plan(names, sizes, n)
    AF.write_text(json.dumps({"prefix": prefix, "slots": slots}, indent=1) + "\n")
    for s, v in slots.items():
        print(f"slot {s}: {len(v)} packages, {sum(len(pk[p]['items']) for p in v)} questions  {v[0]} .. {v[-1]}")
    assert sorted(p for v in slots.values() for p in v) == sorted(names)
    print(f"{len(names)} packages, {total} questions in {len(slots)} slots")


def prompt(slot, only=None, name=None, bundle=None):
    a = json.loads(AF.read_text())
    pk = watch.packages()
    lst = only or a["slots"][slot]
    for p in lst:
        if p not in pk:
            sys.exit(f"unknown package {p}")
    first = pk[lst[0]]
    rows = []
    for p in lst:
        its = pk[p]["items"]
        rows.append(f"- {p} (export {Path(pk[p]['export']).name}): questions {', '.join(str(i.get('number')) for i in its)}; "
                    f"QIDs {' '.join(i['qid'] for i in its)}")
    exports = sorted({pk[p]["export"] for p in lst})
    vals = {
        "@@SLOT@@": name or slot, "@@REPO_SLUG@@": CONFIG["repo_slug"], "@@NQ@@": str(sum(len(pk[p]["items"]) for p in lst)),
        "@@CHAPTER@@": "; ".join(sorted({f"{pk[p].get('book_id', '')} chapter {pk[p].get('chapter_id', '')}: {pk[p].get('chapter_title', '')}"
                                         for p in lst})),
        "@@PKG_TABLE@@": "\n".join(rows), "@@QUEUE_BRANCH@@": CONFIG["queue_branch"],
        "@@EXPORT_CP@@": " ".join(f"work/kq-data/exports/{Path(e).name}" for e in exports),
        "@@EXPORT_CHECK@@": " && ".join(f"KAFU_MOUNTAIN=$PWD python3 /home/user/kq/kafu_queue/preflight.py export work/input/{Path(e).name} | tail -n 1"
                                        for e in exports), "@@ALREADY_LIVE@@": "yes" if first.get("already_live") else "no",
        "@@MAX_MB@@": str(CONFIG["max_package_zip_mb"]), "@@INBOX@@": CONFIG["zip_inbox_url"], "@@NPKG@@": str(len(lst)),
        "@@BUNDLE@@": bundle or "<BUNDLE ASSET ID>", "@@PKG_LIST@@": ",".join(lst),
    }
    text = (HERE / "BUILDER.md").read_text()
    for k, v in vals.items():
        text = text.replace(k, v)
    if "@@" in text:
        sys.exit("unfilled placeholder in BUILDER.md")
    print(text)


def options(prefix, counts=(1, 2, 3, 5, 8, 10, 12, 15, 17, 20, 25, 30, 40, 50), qmin=None):
    """The owner's choice table. Each row assumes 'resize PREFIX N' first: N packages of nearly equal size, one per
    session, so every session finishes at about the same time (no idle sessions, no long tail)."""
    import math
    pk = {k: v for k, v in watch.packages().items() if k.startswith(prefix + "-")}
    led = watch.ledger()
    pk = {k: v for k, v in pk.items() if led.get(k, {}).get("state") != "delivered"}
    if qmin is not None:
        pk = {k: v for k, v in pk.items() if str(v["items"][0].get("number")).isdigit()
              and int(v["items"][0]["number"]) >= qmin}
    if not pk:
        sys.exit(f"no undelivered packages {prefix}-*")
    nq = sum(len(v["items"]) for v in pk.values())
    mpq, setup = CONFIG["minutes_per_question"], CONFIG.get("setup_minutes", 0)
    models = CONFIG["builder_cost_usd"]
    head = sum(CONFIG["head_cost_usd"].values())
    print(f"{nq} questions to build. Measured: {setup} min voice setup per session, then {mpq} min per question. "
          f"Head about ${head:.0f} per run. Each row = resize to N equal packages, one per session.")
    print("sessions | questions per session | hours after the images exist | " + " | ".join(f"$ {m}" for m in models))
    for n in sorted({c for c in counts if c <= nq} | {nq} if nq <= max(counts) else {c for c in counts if c <= nq}):
        per = math.ceil(nq / n)
        if n > 1 and math.ceil(nq / (n - 1)) == per:
            continue                                   # same finish time with one session fewer: not offered
        hours = (setup + per * mpq) / 60
        if hours > 12:
            continue                                   # one lost container would cost too much; autobuild stops at 16 h
        cost = [n * v["session"] + (n * setup + nq * mpq) / 60 * v["per_hour"] + n * v["per_package"]
                for v in models.values()]
        print(f"{n:>8} | {per:>4} | {hours:>6.1f} | " + " | ".join(f"{x:>6.2f}" for x in cost))


def resize(prefix, n, qmin=None):
    from kafu_data import QUEUE, require_data_folder
    require_data_folder()
    pk = {k: v for k, v in watch.packages().items() if k.startswith(prefix + "-")}
    if not pk:
        sys.exit(f"no packages {prefix}-*")
    led = watch.ledger()
    if qmin is not None:                               # only this run's questions (number >= qmin)
        pk = {k: v for k, v in pk.items() if str(v["items"][0].get("number")).isdigit()
              and int(v["items"][0]["number"]) >= qmin}
    busy = [p for p in pk if led.get(p, {}).get("state") in ("building", "delivered")]
    if busy:
        sys.exit("refused: already building or delivered (use --from to pick only this run's questions): " + ",".join(busy))
    if not pk:
        sys.exit("no packages left to repack")
    names = list(pk)                                   # question order (watch.packages sorts by first number)
    head = {k: v for k, v in pk[names[0]].items() if k not in ("package_id", "items")}
    if any(pk[p].get("export") != head.get("export") for p in names):
        sys.exit("refused: the packages come from different exports; resize each export's prefix separately")
    items = [it for p in names for it in pk[p]["items"]]
    n = max(1, min(n, len(items)))
    base, extra = divmod(len(items), n)
    out, i = [], 0
    for k in range(n):
        size = base + (1 if k < extra else 0)
        chunk = items[i:i + size]
        i += size
        a, b = str(chunk[0].get("number")), str(chunk[-1].get("number"))
        name = f"{prefix}-Q{int(a):02d}-{int(b):02d}" if a.isdigit() and b.isdigit() else f"{prefix}-{k + 1:02d}"
        out.append((name, chunk))
    assert sum(len(c) for _, c in out) == len(items) and len({x for x, _ in out}) == n
    for p in names:
        (QUEUE / f"{p}.json").unlink()
    for name, chunk in out:
        (QUEUE / f"{name}.json").write_text(json.dumps({"package_id": name, **head, "items": chunk}, indent=1,
                                                       ensure_ascii=False) + "\n")
    sizes = sorted({len(c) for _, c in out})
    print(f"{len(items)} questions repacked from {len(names)} into {n} packages of {' or '.join(map(str, sizes))} questions:")
    for name, chunk in out:
        print(f"  {name}: {len(chunk)}")
    print(f"next: assign.py split {prefix} {n}   (one package per session)")


def left():
    if not AF.exists():
        sys.exit(f"no slot split in {AF}: run assign.py split first (Head only)")
    a = json.loads(AF.read_text())
    led = watch.ledger()
    n = 0
    for s, v in a["slots"].items():
        todo = [p for p in v if led.get(p, {}).get("state") != "delivered"]
        n += len(todo)
        print(f"slot {s}: {len(v) - len(todo)}/{len(v)} delivered" + (f"; left: {','.join(todo)}" if todo else ""))
    print(f"packages left: {n}")


def main(a):
    if not a:
        sys.exit(__doc__)
    if a[0] == "split":
        if len(a) < 3:
            sys.exit("assign.py split PREFIX N: N is the number of sessions the owner chose")
        split(a[1], int(a[2]), int(a[a.index("--from") + 1]) if "--from" in a else None)
    elif a[0] == "prompt":
        only = a[a.index("--packages") + 1].split(",") if "--packages" in a else None
        name = a[a.index("--as") + 1] if "--as" in a else None
        bundle = a[a.index("--bundle") + 1] if "--bundle" in a else None
        if not bundle:
            sys.exit("--bundle <asset id> is required: bundle.py pack, upload it to the inbox, then pass its asset id")
        prompt(a[1], only, name, bundle)
    elif a[0] == "resize":
        if len(a) < 3:
            sys.exit("assign.py resize PREFIX N: N is the number of sessions the owner chose")
        resize(a[1], int(a[2]), int(a[a.index("--from") + 1]) if "--from" in a else None)
    elif a[0] == "left":
        left()
    elif a[0] == "options":
        options(a[1], qmin=int(a[a.index("--from") + 1]) if "--from" in a else None)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
