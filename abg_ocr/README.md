# ABG Reader Test (Tesseract OCR)

Test page that reads an arterial blood gas (ABG) printout from a phone photo using
[Tesseract.js](https://github.com/naptha/tesseract.js) 5.1.1. OCR runs entirely on the
phone; the photo is never uploaded.

**For testing only. Not for clinical decisions. Every value must be checked against the printout.**

## What it does
1. Photo of the printout → grayscale + adaptive threshold (optional) → Tesseract (LSTM, English).
2. Parses common analyzer labels (Radiometer ABL, RAPIDPoint, GEM style): pH, pCO2, pO2,
   HCO3 (actual/standard), BE, sO2, oximetry, Na/K/Cl/Ca, Glu, Lac, Hb, Hct, FiO2, Temp.
   mmHg and kPa are detected.
3. Safety checks:
   - impossible values (outside physiological range) → red
   - low OCR word confidence → yellow
   - lost decimal point (pH `735`, sO2 `970`) → corrected and flagged yellow
   - Henderson–Hasselbalch: HCO3 = 0.0307 × pCO2(mmHg) × 10^(pH − 6.1) must match the printed HCO3
   - anion gap (Na − Cl − HCO3) must be 0–40
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
