#!/usr/bin/env bash
# One-time setup: build stable-diffusion.cpp (CPU) and download Qwen-Image 2.1 weights (~19 GB).
set -euo pipefail

SD_DIR="${SD_DIR:-/home/user/stable-diffusion.cpp}"
M="${MODELS_DIR:-/home/user/models}"
HF=https://huggingface.co

if [[ ! -x "$SD_DIR/build/bin/sd-cli" ]]; then
  [[ -d "$SD_DIR" ]] || git clone --depth 1 --recursive https://github.com/leejet/stable-diffusion.cpp "$SD_DIR"
  cmake -S "$SD_DIR" -B "$SD_DIR/build" -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=ON
  cmake --build "$SD_DIR/build" -j"$(nproc)" --config Release
fi

mkdir -p "$M"
fetch() { [[ -s "$M/$2" ]] || curl -fSL -o "$M/$2" "$HF/$1"; }
fetch leejet/Qwen-Image-2.1-GGUF/resolve/main/qwen_image_2.1-Q6_K.gguf qwen_image_2.1-Q6_K.gguf
fetch Comfy-Org/Qwen-Image-2.1/resolve/main/vae/qwen_image_2.1_vae_bf16.safetensors qwen_image_2.1_vae_bf16.safetensors
fetch Qwen/Qwen3-VL-8B-Instruct-GGUF/resolve/main/Qwen3VL-8B-Instruct-Q4_K_M.gguf Qwen3VL-8B-Instruct-Q4_K_M.gguf
fetch Comfy-Org/Qwen-Image-2.1/resolve/main/loras/qwen_image_2.1_turbo_lora_avg_rank_178_bf16.safetensors qwen_image_2.1_turbo_lora.safetensors
fetch Qwen/Qwen3-VL-8B-Instruct-GGUF/resolve/main/mmproj-Qwen3VL-8B-Instruct-F16.gguf mmproj-Qwen3VL-8B-Instruct-F16.gguf
echo "Setup complete."
