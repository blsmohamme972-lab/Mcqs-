#!/usr/bin/env bash
# One-time setup for a Claude Code session (Golden rule 8): venv + pinned tools + checksummed model.
# Usage: voiceover/bootstrap.sh      then: ~/.venvs/kafu-voice/bin/python voiceover/voiceover.py make --engine <kokoro|elevenlabs> --workspace work/<batch>
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"; venv="${KAFU_VOICE_VENV:-$HOME/.venvs/kafu-voice}"
command -v ffmpeg >/dev/null || { echo "ffmpeg (with libopus) is required"; exit 1; }
encoders="$(ffmpeg -hide_banner -encoders 2>/dev/null)"   # not `| grep -q`: with pipefail, grep -q exiting early SIGPIPEs ffmpeg
grep -q libopus <<<"$encoders" || { echo "this ffmpeg has no libopus"; exit 1; }
[ -x "$venv/bin/python" ] || python3 -m venv "$venv"
"$venv/bin/pip" install -q -r "$here/requirements.txt"
"$venv/bin/python" "$here/voiceover.py" setup
echo "ready: $venv/bin/python $here/voiceover.py make --engine <kokoro|elevenlabs> --workspace work/<batch>"
