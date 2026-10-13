#!/usr/bin/env python3
"""Run one image trial on CPU: stable-diffusion.cpp + Qwen-Image 2.1.

  run_trial.py NN [--detach] [--set key=value ...] [--no-smoke] [--dry-run]

Does everything for trial NN from trials.json: builds the engine if missing,
downloads only the weights it needs, runs a 1-step smoke test at the SAME size and
CFG (catches out-of-memory before hours are spent), then the full run. Progress is
in out/NN/status.json ("state": setup | smoke | running | done | failed).

Lessons baked in from earlier runs on this 15 GB / 4-core box:
  * GGUF weights only. The int8_convrot checkpoint has a CPU path ~4x slower.
  * --mmap, text encoder on disk, VAE tiling: without them the process was
    OOM-killed at the very end, during the VAE decode, after 40 minutes.
  * Turbo = Q6/Q4 GGUF + turbo LoRA + the 8-step sigma preset, CFG 1.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SD_DIR = Path(os.environ.get("SD_DIR", "/home/user/stable-diffusion.cpp"))
MODELS = Path(os.environ.get("MODELS_DIR", "/home/user/models"))
SD_SHA = "60423ab5f6c4ccffb77e8d45e5b08eb97ca1645d"  # engine commit that was tested
HF = "https://huggingface.co"

# name -> (path in the HF repo, local file name)
FILES = {
    "Q4_K": ("leejet/Qwen-Image-2.1-GGUF/resolve/main/qwen_image_2.1-Q4_K.gguf", "qwen_image_2.1-Q4_K.gguf"),
    "Q5_0": ("leejet/Qwen-Image-2.1-GGUF/resolve/main/qwen_image_2.1-Q5_0.gguf", "qwen_image_2.1-Q5_0.gguf"),
    "Q6_K": ("leejet/Qwen-Image-2.1-GGUF/resolve/main/qwen_image_2.1-Q6_K.gguf", "qwen_image_2.1-Q6_K.gguf"),
    "Q8_0": ("leejet/Qwen-Image-2.1-GGUF/resolve/main/qwen_image_2.1-Q8_0.gguf", "qwen_image_2.1-Q8_0.gguf"),
    "vae": ("Comfy-Org/Qwen-Image-2.1/resolve/main/vae/qwen_image_2.1_vae_bf16.safetensors", "qwen_image_2.1_vae_bf16.safetensors"),
    "te": ("Qwen/Qwen3-VL-8B-Instruct-GGUF/resolve/main/Qwen3VL-8B-Instruct-Q4_K_M.gguf", "Qwen3VL-8B-Instruct-Q4_K_M.gguf"),
    "lora": ("Comfy-Org/Qwen-Image-2.1/resolve/main/loras/qwen_image_2.1_turbo_lora_avg_rank_178_bf16.safetensors", "qwen_image_2.1_turbo_lora.safetensors"),
}


# ---------- config ----------
def load_cfg(tid, extra):
    spec = json.loads((HERE / "trials.json").read_text())
    if tid not in spec["trials"]:
        sys.exit(f"unknown trial {tid}; known: {', '.join(spec['trials'])}")
    cfg = {**spec["defaults"], **spec["trials"][tid]}
    ov_file = HERE / "out" / tid / "overrides.json"
    ov = json.loads(ov_file.read_text()) if ov_file.exists() else {}
    for kv in extra or []:
        k, _, v = kv.partition("=")
        ov[k] = v
    cfg.update({k: coerce(cfg.get(k), v) for k, v in ov.items()})
    if ov:
        ov_file.parent.mkdir(parents=True, exist_ok=True)
        ov_file.write_text(json.dumps(ov, indent=1))
    cfg["overrides"] = ov
    return cfg


def coerce(old, v):
    if not isinstance(v, str):
        return v
    if isinstance(old, bool):
        return v.lower() in ("1", "true", "yes", "on")
    if isinstance(old, int):
        return int(v)
    if isinstance(old, float):
        return float(v)
    return v


# ---------- status ----------
class Status:
    def __init__(self, d):
        self.path = d / "status.json"
        self.data = {}

    def set(self, **kw):
        self.data.update(kw, updated=time.strftime("%Y-%m-%d %H:%M:%S"))
        self.path.write_text(json.dumps(self.data, indent=1))


def run(cmd, **kw):
    subprocess.run(cmd, check=True, **kw)


# ---------- setup ----------
def ensure_engine(log):
    exe = SD_DIR / "build/bin/sd-cli"
    if exe.exists():
        return exe
    log("building engine")
    SD_DIR.mkdir(parents=True, exist_ok=True)
    if not (SD_DIR / ".git").exists():
        run(["git", "init", "-q"], cwd=SD_DIR)
        run(["git", "remote", "add", "origin", "https://github.com/leejet/stable-diffusion.cpp"], cwd=SD_DIR)
    try:
        run(["git", "fetch", "-q", "--depth", "1", "origin", SD_SHA], cwd=SD_DIR)
        run(["git", "checkout", "-q", "FETCH_HEAD"], cwd=SD_DIR)
    except subprocess.CalledProcessError:
        log("pinned commit not fetchable, using default branch")
        run(["git", "fetch", "-q", "--depth", "1", "origin", "master"], cwd=SD_DIR)
        run(["git", "checkout", "-q", "FETCH_HEAD"], cwd=SD_DIR)
    run(["git", "submodule", "update", "--init", "--recursive", "--depth", "1"], cwd=SD_DIR)
    run(["cmake", "-S", str(SD_DIR), "-B", str(SD_DIR / "build"), "-DCMAKE_BUILD_TYPE=Release", "-DGGML_NATIVE=ON"],
        stdout=subprocess.DEVNULL)
    run(["cmake", "--build", str(SD_DIR / "build"), "-j", str(os.cpu_count()), "--config", "Release", "--target", "sd-cli"],
        stdout=subprocess.DEVNULL)
    return exe


def remote_size(url):
    out = subprocess.run(["curl", "-sIL", url], capture_output=True, text=True).stdout
    sizes = re.findall(r"(?im)^content-length:\s*(\d+)", out)
    return int(sizes[-1]) if sizes else None


def fetch(key, log):
    path, local = FILES[key]
    url = f"{HF}/{path}"
    dest = MODELS / local
    want = remote_size(url)
    for attempt in range(1, 7):
        if dest.exists() and want and dest.stat().st_size == want:
            return
        log(f"downloading {local} (attempt {attempt}, want {want})")
        subprocess.run(["curl", "-fL", "-C", "-", "--retry", "3", "--retry-delay", "5", "-o", str(dest), url])
    sys.exit(f"download failed: {local}")


def needed(cfg):
    keys = [cfg["quant"], "vae", "te"]
    return keys + (["lora"] if cfg["turbo"] else [])


# ---------- command ----------
def build_cmd(cfg, exe, out, smoke):
    prompt = (HERE / "prompts" / f"{cfg['prompt']}.txt").read_text().strip()
    cmd = [str(exe), "--diffusion-model", str(MODELS / FILES[cfg["quant"]][1]),
           "--vae", str(MODELS / FILES["vae"][1]), "--llm", str(MODELS / FILES["te"][1]),
           "--sampling-method", "euler", "--fa", "--mmap", "--params-backend", "te=disk",
           "--vae-tiling", "--vae-tile-overlap", "0.25",
           "-W", str(cfg["W"]), "-H", str(cfg["H"]), "-t", str(os.cpu_count()),
           "-s", str(cfg["seed"]), "-o", str(out)]
    if cfg["offload"]:
        cmd.append("--offload-to-cpu")
    if cfg["turbo"]:
        prompt += "<lora:qwen_image_2.1_turbo_lora:1>"
        cmd += ["--lora-model-dir", str(MODELS), "--cfg-scale", "1.0"]
        cmd += ["--sigmas", "1.0,0.0" if smoke else "qwen-image-2.1-turbo"]
        cmd += ["--steps", "1" if smoke else "8"]
    else:
        neg = (HERE / "prompts" / "negative.txt").read_text().strip()
        cmd += ["--steps", "1" if smoke else str(cfg["steps"]), "--cfg-scale", str(cfg["cfg"]), "-n", neg]
    cache = cfg["cache"]
    if cache == "off":
        cmd += ["--model-args", "qwen_image_2_1_prefix_cache=false"]
    elif cache != "auto":
        cmd += ["--model-args", f"qwen_image_2_1_prefix_cache_type={cache}"]
    return cmd + ["-p", prompt]


def execute(cmd, logfile, status, label, total_steps):
    """Run cmd, track peak RSS and step progress. Returns (returncode, seconds, peak_mb)."""
    t0, peak = time.time(), 0
    with open(logfile, "wb") as lf:
        p = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT)
        while p.poll() is None:
            try:
                for line in open(f"/proc/{p.pid}/status"):
                    if line.startswith("VmHWM:"):
                        peak = max(peak, int(line.split()[1]) // 1024)
            except OSError:
                pass
            with open(logfile, "rb") as f:
                f.seek(0, 2)
                f.seek(max(0, f.tell() - 3000))
                m = re.findall(rb"(\d+)/(\d+) - ([\d.]+)s/it", f.read())
            step = f"{m[-1][0].decode()}/{m[-1][1].decode()} ({m[-1][2].decode()}s/step)" if m else "starting"
            status.set(state=label, step=step, peak_rss_mb=peak, elapsed_min=round((time.time() - t0) / 60, 1))
            time.sleep(10)
    return p.returncode, round(time.time() - t0), peak


def grab(logfile, pattern):
    m = re.findall(pattern, Path(logfile).read_bytes().decode(errors="ignore"))
    return float(m[-1]) if m else None


def tail(logfile, n=25):
    lines = Path(logfile).read_bytes().decode(errors="ignore").replace("\r", "\n").splitlines()
    return [l for l in lines if l.strip() and "|" not in l[:6]][-n:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tid")
    ap.add_argument("--detach", action="store_true")
    ap.add_argument("--set", nargs="*", dest="extra", help="override config, e.g. quant=Q4_K cache=off W=640")
    ap.add_argument("--no-smoke", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args()

    cfg = load_cfg(a.tid, a.extra)
    d = HERE / "out" / a.tid
    d.mkdir(parents=True, exist_ok=True)
    exe = SD_DIR / "build/bin/sd-cli"

    if a.dry_run:
        print(json.dumps({k: v for k, v in cfg.items() if k != "why"}, indent=1))
        print("SMOKE:", " ".join(build_cmd(cfg, exe, d / "smoke.png", True)[:-1]), "-p <prompt>")
        print("FULL: ", " ".join(build_cmd(cfg, exe, d / "image.png", False)[:-1]), "-p <prompt>")
        print("needs:", needed(cfg))
        return

    if a.detach and not a.child:
        st = d / "status.json"
        if st.exists() and json.loads(st.read_text()).get("state") in ("setup", "smoke", "running"):
            age = time.time() - st.stat().st_mtime
            if age < 120:
                sys.exit("already running (status updated <2 min ago)")
        st.unlink(missing_ok=True)
        args = [sys.executable, __file__, a.tid, "--child"] + (["--no-smoke"] if a.no_smoke else [])
        subprocess.Popen(["setsid", "nohup"] + args, stdout=open(d / "runner.log", "ab"), stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, cwd=HERE)
        print(f"started trial {a.tid}; watch {d / 'status.json'}")
        return

    status = Status(d)
    log = lambda m: status.set(state="setup", note=m)
    status.set(state="setup", config={k: v for k, v in cfg.items() if k not in ("why",)}, started=time.strftime("%H:%M:%S"))
    t_start = time.time()
    try:
        exe = ensure_engine(log)
        MODELS.mkdir(parents=True, exist_ok=True)
        for key in needed(cfg):
            fetch(key, log)
    except (subprocess.CalledProcessError, SystemExit) as e:
        status.set(state="failed", stage="setup", error=str(e))
        sys.exit(1)

    result = {"id": a.tid, "name": cfg["name"], "config": cfg, "setup_min": round((time.time() - t_start) / 60, 1)}

    if cfg["smoke"] and not a.no_smoke:
        rc, secs, peak = execute(build_cmd(cfg, exe, d / "smoke.png", True), d / "smoke.log", status, "smoke", 1)
        result.update(smoke_seconds=secs, smoke_peak_rss_mb=peak)
        if rc != 0 or not (d / "smoke.png").exists():
            status.set(state="failed", stage="smoke", exit_code=rc, oom=rc in (-9, 137), peak_rss_mb=peak,
                       log_tail=tail(d / "smoke.log"))
            (d / "result.json").write_text(json.dumps(result, indent=1))
            sys.exit(1)

    rc, secs, peak = execute(build_cmd(cfg, exe, d / "image.png", False), d / "run.log", status, "running", cfg["steps"])
    result.update(exit_code=rc, run_seconds=secs, peak_rss_mb=peak,
                  sampling_seconds=grab(d / "run.log", r"sampling completed, taking ([\d.]+)s"),
                  decode_seconds=grab(d / "run.log", r"decode_first_stage completed, taking ([\d.]+)s"))
    (d / "result.json").write_text(json.dumps(result, indent=1))
    if rc != 0 or not (d / "image.png").exists():
        status.set(state="failed", stage="run", exit_code=rc, oom=rc in (-9, 137), peak_rss_mb=peak, log_tail=tail(d / "run.log"))
        sys.exit(1)
    status.set(state="done", peak_rss_mb=peak, run_minutes=round(secs / 60, 1), image=str(d / "image.png"))


if __name__ == "__main__":
    main()
