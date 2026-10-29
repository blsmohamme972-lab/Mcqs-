# Kafu MotionCards scene toolkit (legacy v1)

> **RETIRED (Oct 2026). Do not use this to make new content.** The owner stopped hand-animated MotionCards.
> New work is IMAGE LESSONS only: follow `motioncards/LESSON_PROMPT.md`. This file is kept only as background for
> the shared scaffold/package/validate tools.

> New cards should use schema v2. See `AUTHORING_V2.md`. This page documents the v1 engine, which remains supported unchanged for existing scenes.

The v1 toolkit is intentionally small. Scene authors describe **what changes over time**; the compiler/player own responsive framing and time.

Every layer lives in a 640×440 SVG coordinate system and supports a bounded active interval.

## Primitive patterns

### Arrow / direction
Use `arrow` to teach flow, migration, nerve direction, pressure relationships, movement or sequence.

### Highlight
Use `highlight` behind the one structure/value that matters. Animate opacity rather than flashing.

### Focus
Use `focus` as a calm bounding region around the key structure. Keep unrelated structures faint or absent.

### Labels
Use `label` for only essential words/numbers. Prefer <40 characters.

### Paths
Use `path` for original schematic geometry. Never trace/copy copyrighted source artwork.

### Layered structures
Stack `rect`, `circle` and `path` layers from broad anatomy to the one relevant relationship.

### Sequences
Give layers staggered `start_ms` / `end_ms`. Avoid independent loops.

### Cause → effect
Place two compact structures and one arrow; reveal cause, then relation, then effect. Do not add distractor mechanisms.

## Timing

`from` and `to` may animate numeric `x`, `y`, `scale`, and `opacity`.

The host supplies an exact timestamp, so seeking backward reproduces the earlier frame.

## Custom renderer

For a rare scene that needs geometry not expressible through primitives, a scene JSON may include a deterministic JavaScript string defining:

`function renderCustom(art,timeMs,helpers) { ... }`

It is compiled statically; no eval/new Function is used. Network, storage, workers, timers and navigation APIs are rejected. The function must depend only on `timeMs`, scene constants and supplied helpers.
