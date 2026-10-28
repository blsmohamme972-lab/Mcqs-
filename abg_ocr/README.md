# ABG Reader Test (Tesseract OCR)

Test page that reads an arterial blood gas (ABG) printout from a phone photo using
[Tesseract.js](https://github.com/naptha/tesseract.js) 5.1.1. OCR runs entirely on the
phone; the photo is never uploaded.

**For testing only. Not for clinical decisions. Every value must be checked against the printout.**

## What it does
1. Photo of the printout → automatic deskew (projection profile) → grayscale + adaptive threshold
   (optional) → Tesseract (LSTM, English). A label with no number on its own OCR line is paired with
   the nearest number on the same printed row by word position (Radiometer prints values in a column).
2. Parses common analyzer labels (Radiometer ABL, RAPIDPoint, GEM style): pH, pCO2, pO2,
   HCO3 (actual/standard), BE, sO2, oximetry, Na/K/Cl/Ca, Glu, Lac, Hb, Hct, FiO2, Temp.
   mmHg and kPa are detected.
3. Safety checks:
   - impossible values (outside physiological range) → red
   - low OCR word confidence → yellow
   - lost decimal point (pH `735`, sO2 `970`) → corrected and flagged yellow
   - Henderson–Hasselbalch: HCO3 = 0.0307 × pCO2(mmHg) × 10^(pH − 6.1) must match the printed HCO3
   - anion gap (Na − Cl − HCO3) must be 0–40
   - BE vs pH/HCO3 (Van Slyke): BEecf ≈ 0.93 × (HCO3 − 24.4 + 14.8 × (pH − 7.4))
   - pO2 vs sO2 (Severinghaus) when pO2 < 100 mmHg
   - same number under two labels (label misread, e.g. pCO2 read as "po,")
   - no decimal point on a value the analyzer always prints with one
4. User corrects values and taps "record", which logs per-device accuracy (localStorage).

## Files
- `index.html` — the page (Tesseract loaded from jsDelivr).
- `tess/eng.traineddata.gz.wasm` — `@tesseract.js-data/eng` 4.0.0_best_int (gzip). Named `.wasm`
  so the artifact host serves it; a worker shim redirects Tesseract's request to it.

## Run locally
```
cd abg_ocr && python3 -m http.server 8000
# open http://localhost:8000 (or the PC's LAN IP from an Android phone on the same Wi-Fi)
```

## Known results on synthetic printouts
Most values read correctly; typical Tesseract errors are 0↔6 swaps (101→161, 37.0→37.6) and lost
decimals. Range/HH/anion-gap checks catch many but not all (e.g. Lac 1.1 read as 5.4 passed every check).

## Real Radiometer ABL800 FLEX photo (tilted ~6°, second sheet in frame)
Without deskew almost nothing was read. With deskew + row pairing: 9 values correct (pCO2, HCO3 std,
sO2, FO2Hb, Na, Ca, Glu, Lac, …), pH / HCO3 / K / Cl missing, and wrong values including pO2 36.6
(true 204, "pCO2" read as "po,"), BE 22 (true −2.2), FHHb 11 (1.1), FMetHb 20 (2.0). The pO2 error is
caught by the sO2 and duplicate-number checks; decimal losses are flagged yellow.

## Android app (APK)
`android/` wraps the same page in a WebView with every Tesseract file bundled, so it works offline.
The page is served from assets through `WebViewAssetLoader`; the camera/gallery picker is wired in
`MainActivity`. A test build is in `release/ABG-Reader-test.apk` (debug-signed).

Build:
```
cd abg_ocr/android
./prepare_assets.sh          # copies index.html + Tesseract into app/src/main/assets
echo "sdk.dir=$ANDROID_HOME" > local.properties
gradle assembleDebug         # → app/build/outputs/apk/debug/app-debug.apk
```

## v0.2: ABL800 decimal profile
Tesseract often drops the decimal point (2.9 → "29", 0.6 → "06"). With "Radiometer ABL800" selected,
values the ABL800 prints with fixed decimals (pH 3, Ca 2, most others 1) get the point re-inserted
and are flagged yellow. Arrow flags read as letters ("↑ cK⁺" → "Tock", "↓ ctHb" → "d ctHb") are handled.
Result on a straight photo of a real ABL800 printout: 20/20 values correct, HH/BE/anion-gap checks pass.

## v0.3: cross-check against the analyzer's own calculated values
The ABL800 prints Anion Gap (Na − Cl − HCO3), AnionGap,K (+K) and mOsm (2·Na + Glu). These are now
read and compared with the values read for Na, K, Cl, HCO3 and Glu. On a phone OCR run Na 152 was
read as 162; it passed the range and HH checks but is now caught by both the anion gap and mOsm checks.
