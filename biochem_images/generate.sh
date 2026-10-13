#!/usr/bin/env bash
# Generate a biochemistry illustration with Qwen-Image 2.1 (CPU, stable-diffusion.cpp).
#
# Usage:
#   ./generate.sh "prompt" output.png [turbo|base] [WIDTHxHEIGHT]
#   REF=input.png ./generate.sh "edit instruction" output.png [turbo|base] [WIDTHxHEIGHT]
#
# Run ./setup.sh once per fresh container to build the engine and download weights.
set -euo pipefail

PROMPT="${1:?prompt required}"
OUT="${2:?output path required}"
MODE="${3:-turbo}"
SIZE="${4:-1024x1024}"
W="${SIZE%x*}"
H="${SIZE#*x}"

SD="${SD_DIR:-/home/user/stable-diffusion.cpp}/build/bin/sd-cli"
M="${MODELS_DIR:-/home/user/models}"

COMMON=(--vae "$M/qwen_image_2.1_vae_bf16.safetensors"
        --llm "$M/Qwen3VL-8B-Instruct-Q4_K_M.gguf"
        --sampling-method euler --offload-to-cpu --fa
        --mmap --params-backend te=disk --vae-tiling --vae-tile-overlap 0.25
        -W "$W" -H "$H" -t "$(nproc)" -p "$PROMPT" -o "$OUT")

if [[ -n "${REF:-}" ]]; then
  # Image editing: the text encoder needs its vision weights to read the reference.
  COMMON=(--llm_vision "$M/mmproj-Qwen3VL-8B-Instruct-F16.gguf" -r "$REF" "${COMMON[@]}")
fi

if [[ "$MODE" == "turbo" ]]; then
  # Q6_K GGUF + Turbo LoRA: 8 steps, no CFG. GGUF uses ggml's SIMD CPU kernels;
  # the int8_convrot Turbo checkpoint only has a slow portable CPU path.
  COMMON[${#COMMON[@]}-3]="$PROMPT<lora:qwen_image_2.1_turbo_lora:1>"
  "$SD" --diffusion-model "$M/qwen_image_2.1-Q6_K.gguf" --lora-model-dir "$M" \
    --sigmas qwen-image-2.1-turbo --steps 8 --cfg-scale 1.0 "${COMMON[@]}"
else
  # Full model with CFG: slower, highest quality.
  "$SD" --diffusion-model "$M/qwen_image_2.1-Q6_K.gguf" \
    --steps "${STEPS:-30}" --cfg-scale 6.0 "${COMMON[@]}"
fi
