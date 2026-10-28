# MCQs — Android app

Personal study app: spaced-repetition cards (FSRS-6) mixed with visual-mnemonic scenes and videos.
Content arrives as a zip package (see [`../docs/package-format.md`](../docs/package-format.md)).

## What's in v0.1

| Feature | Notes |
|---|---|
| Import zip | "Import zip" button → system file picker. Re-importing the same package id updates it and keeps review history. |
| Card types | `occlusion` (scene image, hide-all-guess-one, ~0.2 s reveal), `mcq` (options reshuffled daily; a wrong pick allows only *Again*), `basic`. |
| Scheduling | FSRS-6, ported from py-fsrs 6.3.2 and checked against it on 1,326 reviews. Learning steps 1 m / 10 m, relearning 10 m, 90 % retention, 20 new cards/day, day starts 04:00. |
| Scenes | Per-deck scene list; scene page plays the video (Media3) and shows the image with optional region labels and the story. Pinch-zoom on all scene images. |
| Offline | Everything is stored on the phone; no account, no network. |

## Build

Needs JDK 17+ and the Android SDK (platform 35).

```bash
cd android
./gradlew testDebugUnitTest   # FSRS golden tests, zip importer tests, Robolectric end-to-end UI test
./gradlew assembleDebug       # → app/build/outputs/apk/debug/app-debug.apk
```

## Make a content package

```bash
python3 tools/build_package.py samples/tension_pneumothorax dist/ct-ch17-sample.zip
```

Copy the zip to the phone and import it in the app.

## Layout

```
app/src/main/java/com/mcqs/app/
├── srs/Fsrs.kt          FSRS-6 scheduler
├── pkg/                 manifest model + validation, safe zip extraction
├── data/                Room database, repository (import, queue, answering)
└── ui/                  Compose screens: home, study, scenes, scene image with occlusion
```
