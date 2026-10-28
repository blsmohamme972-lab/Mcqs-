# Content package format (v1)

A package is a `.zip` with `manifest.json` at its root and the media it references.
Build one from a folder with `python3 tools/build_package.py <folder> <out.zip>`, which runs
the same validation as the app's importer.

```
ct-ch17.zip
├── manifest.json
└── media/
    ├── tension_ptx.png      scene image (occlusion cards are drawn on it)
    └── tension_ptx.mp4      optional scene video (code-animated + TTS)
```

## manifest.json

```json
{
  "format": 1,
  "id": "ct-ch17",
  "title": "Ch17 Chest trauma",
  "version": 3,
  "source": "Cardiothoracic Surgery, 2nd ed.",
  "scenes": [
    {
      "id": "tension_ptx",
      "title": "Tension pneumothorax",
      "image": "media/tension_ptx.png",
      "video": "media/tension_ptx.mp4",
      "story": "Optional narrative shown on the scene page",
      "source": "Ch17 p823",
      "regions": [
        { "id": "firefighter", "x": 0.75, "y": 0.15, "w": 0.23, "h": 0.22, "label": "Hero needle" }
      ]
    }
  ],
  "cards": [
    { "id": "ptx.firefighter", "type": "occlusion", "scene": "tension_ptx", "region": "firefighter",
      "front": "Immediate decompression: what, and where?",
      "back": "Wide-bore needle, 2nd ICS, midclavicular line.", "source": "Ch17 p823", "tags": ["ch17"] },
    { "id": "ptx.mcq.needle", "type": "mcq", "front": "…", "options": ["A", "B", "C", "D"], "answer": 0,
      "explanation": "…" },
    { "id": "ch17.box17_1", "type": "basic", "front": "…", "back": "…", "image": "media/optional.png" }
  ]
}
```

### Rules

| Field | Rule |
|---|---|
| `format` | Must be `1`. |
| `id` (package, scene, card) | `[A-Za-z0-9._-]`, max 128 chars, unique within its list. |
| `version` | Bump when you re-export; shown in the app. |
| `regions[].x/y/w/h` | Fractions of the image (0–1), origin top-left. |
| `occlusion` card | Needs `scene` (with an `image`), an existing `region`, and `back`. |
| `mcq` card | At least 2 `options`; `answer` is the 0-based index of the correct one. Options are shuffled daily in the app. |
| `basic` card | Needs `back`; `image` is optional. |
| Media paths | Relative to the zip root, must exist in the zip. |

Unknown fields are ignored, so newer tools can add fields without breaking older app versions.

## Publishing (automatic)

Put each package folder under `content/<package-id>/`. Every push that touches `content/`,
`android/` or `tools/` runs `.github/workflows/publish.yml`, which:

1. runs the app's tests and builds a signed APK (version code = 100 + run number);
2. zips every `content/*` folder (deterministic zips: unchanged content keeps the same sha256);
3. writes `index.json` (app version + each package's URL and sha256);
4. publishes them as a GitHub release `v0.2.<run>` (the newest 10 are kept).

The app reads `releases/latest/download/index.json` when it opens (at most every 2 minutes, or
via the refresh button), downloads packages whose sha256 changed, and offers the new APK when its
version code is higher. Android always asks you to confirm an app install.

## Updating a package

Re-import a zip with the **same package `id`** to update it:

- Cards keep their review history as long as their **card `id` is unchanged** — never rename ids
  just to reword a card; edit `front`/`back` instead.
- Cards missing from the new version are deactivated (hidden, history kept).
- Scenes and media are replaced wholesale.

## Occlusion behaviour

The asked region is masked in the accent colour; every other region gets a neutral mask
("hide all, guess one") so mask shapes don't leak answers. On reveal the asked mask fades out
in ~0.2 s and the region is outlined. Pinch to zoom, double-tap to reset.
