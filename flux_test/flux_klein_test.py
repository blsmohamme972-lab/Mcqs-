"""Minimal FLUX 3 Image Klein (distilled) cost test on Modal.

- Downloads only the distilled diffusers weights (no -base, no fp8/nvfp4 variants)
  on a CPU container into a Modal Volume.
- Generates exactly one image (16 steps) on an A100, timeout 8 min, scaledown 2 s.

Run:  modal run flux_test/flux_klein_test.py
"""
import os
import time

import modal

REPO = "black-forest-labs/flux-3-image-klein"
WEIGHTS = "/weights/flux-3-image-klein"
PROMPT = (
    "A wide-angle photograph of a lone American bison in a misty geothermal "
    "landscape, half hidden by white steam, soft overcast light."
)

app = modal.App("flux-klein-distilled-cost-test")
vol = modal.Volume.from_name("flux-klein-weights", create_if_missing=True)
hf_secret = modal.Secret.from_dict({"HF_TOKEN": os.environ.get("HF_TOKEN", "")})

cpu_image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "huggingface_hub[hf_transfer]==0.35.3"
).env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})

gpu_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install(
        "torch==2.8.0",
        "transformers",
        "accelerate",
        "safetensors",
        "sentencepiece",
        "git+https://github.com/huggingface/diffusers.git",
    )
)


@app.function(image=cpu_image, volumes={"/weights": vol}, secrets=[hf_secret],
              cpu=2, memory=2048, timeout=1800)
def download():
    from huggingface_hub import snapshot_download

    if os.path.exists(f"{WEIGHTS}/.done"):
        print("weights already cached")
        return
    t = time.time()
    snapshot_download(
        repo_id=REPO,
        local_dir=WEIGHTS,
        # diffusers layout only: ~20 GB instead of the full 43 GB repo
        allow_patterns=["modular_model_index.json", "transformer/*",
                        "text_encoder/*", "vae/*"],
    )
    open(f"{WEIGHTS}/.done", "w").close()
    vol.commit()
    print(f"download done in {time.time() - t:.0f}s")


@app.function(image=gpu_image, gpu="A100-40GB", volumes={"/weights": vol},
              timeout=480, scaledown_window=2, max_containers=1)
def generate() -> bytes:
    import io

    import torch
    from diffusers import ModularPipeline

    t = time.time()
    pipe = ModularPipeline.from_pretrained(WEIGHTS)
    pipe.load_components(dtype=torch.bfloat16)
    pipe.to("cuda")
    print(f"load: {time.time() - t:.0f}s")

    t = time.time()
    img = pipe(prompt=PROMPT, num_inference_steps=16,
               generator=torch.Generator().manual_seed(0), output="images")[0]
    print(f"generate (16 steps): {time.time() - t:.1f}s")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@app.local_entrypoint()
def main():
    download.remote()
    png = generate.remote()
    out = os.path.join(os.path.dirname(__file__), "klein_distilled.png")
    with open(out, "wb") as f:
        f.write(png)
    print("saved", out)
