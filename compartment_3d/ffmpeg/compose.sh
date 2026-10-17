#!/usr/bin/env bash
# Compose the 30 s lesson video from three layers. Video only: no audio track.
#
#   layer 1  3D scene    compartment_3d.html#clean recorded frame by frame
#                        (node ../record_frames.mjs <orient> <frames dir>)
#   layer 2  chart       Manim, transparent  (manim -qh -t --fps 30 ../manim/pressure_curve.py PressureCurve)
#   layer 3  captions    ASS from captions.py, burned in by libass (Arabic shaped RTL)
#
# Then a light grade (contrast, saturation, vignette) and H.264 for YouTube / TikTok / Reels.
#
# Usage:
#   ./compose.sh 16x9 <frames dir> <chart.mov> <out.mp4>
#   ./compose.sh 9x16 <frames dir> <chart.mov> <out.mp4>
#   ./compose.sh --check 16x9|9x16     validate the filter graph on 2 s of test input, write nothing
#
# FONTS_DIR (optional) points libass at Archivo / IBM Plex Sans Arabic .ttf files.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
FONTS_DIR="${FONTS_DIR:-$HERE/fonts}"
CHART_START=11.0   # seconds into the lesson where the Manim chart appears
CHART_LEN=13.4     # length of PressureCurve

check=0
if [[ "${1:-}" == "--check" ]]; then check=1; shift; fi
ORIENT="${1:?orientation 16x9 or 9x16}"

case "$ORIENT" in
  16x9) W=1920; H=1080; CHART_W=620;  CHART_X="W-w-48";     CHART_Y=48 ;;
  9x16) W=1080; H=1920; CHART_W=1000; CHART_X="(W-w)/2";    CHART_Y=150 ;;
  *) echo "orientation must be 16x9 or 9x16" >&2; exit 2 ;;
esac

ASS="$HERE/build/captions_${ORIENT}.ass"
mkdir -p "$HERE/build"
python3 "$HERE/captions.py" "$HERE/build" >/dev/null

if (( check )); then
  # Stand-ins with the real sizes; chart shifted to 0.5 s so it shows inside 2 s.
  IN_3D=(-f lavfi -i "testsrc2=s=${W}x${H}:r=30:d=2")
  IN_CHART=(-f lavfi -i "color=c=black@0.0:s=960x640:r=30:d=2,format=rgba")
  START=0.5; LEN=1.4
  OUT=(-f null -)
else
  FRAMES="${2:?frames dir}"; CHART="${3:?chart .mov}"; OUTFILE="${4:?out .mp4}"
  IN_3D=(-framerate 30 -i "$FRAMES/f%04d.jpg")
  IN_CHART=(-i "$CHART")
  START=$CHART_START; LEN=$CHART_LEN
  OUT=(-c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p -movflags +faststart "$OUTFILE")
fi

FADE_OUT=$(python3 -c "print(round($LEN - 0.4, 2))")
GRAPH="
[1:v]format=rgba,
     fade=t=in:st=0:d=0.4:alpha=1,fade=t=out:st=${FADE_OUT}:d=0.4:alpha=1,
     scale=${CHART_W}:-1:flags=lanczos,
     setpts=PTS-STARTPTS+${START}/TB[chart];
[0:v]scale=${W}:${H}:flags=lanczos,setsar=1[base];
[base][chart]overlay=x=${CHART_X}:y=${CHART_Y}:eof_action=pass:format=auto[layered];
[layered]eq=contrast=1.04:saturation=1.08,
         vignette=angle=PI/6,
         subtitles=filename='${ASS}':fontsdir='${FONTS_DIR}',
         format=yuv420p[v]"

ffmpeg -hide_banner -loglevel warning -y "${IN_3D[@]}" "${IN_CHART[@]}" \
  -filter_complex "$GRAPH" -map "[v]" -an -r 30 "${OUT[@]}"

(( check )) && echo "filter graph OK for $ORIENT (nothing written)"
