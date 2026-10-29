#!/bin/bash
# Head: build one MCARDS lesson package from finished lessons, checked end to end.
#   tools/kafu_voice/build_pkg.sh EXPORT.json PKGID LESSONS_DIR OUT_DIR CATALOG_URL QID...
# LESSONS_DIR holds <QID>.lesson.json + <QID>.png; the voice must already be imported (import_voice.py).
# Keep a package at 12 lessons or fewer: the download page takes at most 20 MB per file (base64 grows it by a third),
# and `package` splits anything larger into ~6 MB parts by itself.
# CATALOG_URL is required: without it `package` fails with source_provenance_url_invalid:catalog_url.
set -e
EXPORT=$1 P=$2 L=$3 OUT=$4 CAT=$5; shift 5
cd "$(dirname "$0")/../.."
W=$OUT/ws_$P; rm -rf "$W"; Q=""; for n in "$@"; do Q="$Q $n"; done
python3 tools/motioncards.py scaffold "$EXPORT" --out "$W" --package-id "$P" --revision 1 --qids $Q --duration-ms 30000 >/dev/null
mkdir -p "$W/lessons"; for q in "$@"; do cp "$L/$q.lesson.json" "$L/$q.png" "$W/lessons/"; done
python3 - "$W/selection.json" "$CAT" <<'PY'
import json, sys
p, cat = sys.argv[1], sys.argv[2]; d = json.load(open(p)); d["source"]["catalog_url"] = cat
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
PY
~/.venvs/kafu-voice/bin/python tools/motioncards.py lesson --workspace "$W" >/dev/null
python3 tools/motioncards.py lint --workspace "$W" | grep -c PASS
Z=$OUT/MCARDS_${P}_r1.zip
python3 tools/motioncards.py package "$EXPORT" --workspace "$W" --out "$Z" >/dev/null
python3 tools/motioncards.py validate "$Z" | grep -E '"status"|animations'
ls -l "$Z" | awk '{print $5}'; sha256sum "$Z" | cut -c1-64
