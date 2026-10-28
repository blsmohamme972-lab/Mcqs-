#!/usr/bin/env bash
# Copies the ABG page and Tesseract files into app/src/main/assets for an offline build.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out="$here/app/src/main/assets"
tmp="$(mktemp -d)"
rm -rf "$out" && mkdir -p "$out/tess/core"
(cd "$tmp" && npm pack --silent tesseract.js@5.1.1 tesseract.js-core@5.1.1 >/dev/null \
  && tar xzf tesseract.js-5.1.1.tgz && mkdir core && tar xzf tesseract.js-core-5.1.1.tgz -C core)
cp "$tmp/package/dist/tesseract.min.js" "$tmp/package/dist/worker.min.js" "$out/tess/"
cp "$tmp/core/package/tesseract-core-simd-lstm.wasm.js" "$tmp/core/package/tesseract-core-lstm.wasm.js" "$out/tess/core/"
cp "$here/../tess/eng.traineddata.gz.wasm" "$out/tess/"
sed -e 's#https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/#tess/#g' \
    -e 's#https://cdn.jsdelivr.net/npm/tesseract.js-core@5.1.1#tess/core#g' \
    "$here/../index.html" > "$out/index.html"
rm -rf "$tmp"
grep -c "cdn.jsdelivr" "$out/index.html" && { echo "CDN reference left in page" >&2; exit 1; } || true
echo "assets ready: $(du -sh "$out" | cut -f1)"
