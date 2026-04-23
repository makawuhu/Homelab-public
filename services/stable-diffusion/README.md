# Stable Diffusion

This service has two components: a persistent **WebUI** on VM 101 and a one-shot **job runner** for the GPU API (VM 131).

---

## Job Runner (gpu API)

A lightweight diffusers-based container that runs as a `custom_docker` job on the GPU API. Takes env vars, generates one image, writes it to `/opt/outputs`, prints the filename to stdout, and exits.

**Host:** VM 131 (`192.168.x.167`)
**Model storage:** `/opt/models/` (world-writable)
**Output storage:** `/opt/outputs/` (world-writable)
**Output URL base:** `https://gpu-outputs.yourdomain.com/`

### Files

| File | Purpose |
|------|---------|
| `Dockerfile.job` | Builds `sd-job:local` — PyTorch 2.3 + diffusers + transformers 4.x |
| `generate.py` | Entrypoint: reads env vars, generates image, saves to `/output/{uuid}.png`, prints filename |
| `build-job.sh` | Builds `sd-job:local` directly on VM 131 (root@192.168.x.167) |
| `download-model.sh` | Downloads SD 1.5 safetensors to `/opt/models` on VM 131 |
| `test-job.sh` | Submits a test job and polls until complete, prints output URL |

### Deployment

```bash
# One-time: download model (~4GB)
./download-model.sh

# Build the job runner image on VM 131
./build-job.sh

# Test end-to-end
./test-job.sh
```

### SSH path

CT 102 SSHes directly to VM 131 as `root@192.168.x.167`.

### Job payload

```json
{
  "job_type": "custom_docker",
  "timeout_seconds": 180,
  "payload": {
    "image": "sd-job:local",
    "env": {
      "PROMPT": "your prompt here",
      "NEGATIVE_PROMPT": "blurry, low quality",
      "STEPS": "20",
      "WIDTH": "512",
      "HEIGHT": "512",
      "MODEL_PATH": "/models/v1-5-pruned-emaonly.safetensors",
      "GUIDANCE_SCALE": "7.5",
      "SEED": "optional"
    },
    "volumes": {
      "/opt/models": "/models",
      "/opt/outputs": "/output"
    },
    "shm_size": "2g"
  }
}
```

Result filename is in `result.stdout`. Full URL: `https://gpu-outputs.yourdomain.com/{filename}`.

### Dependency notes

- `transformers` must be `<5.0.0` — 5.x requires PyTorch >= 2.4, base image has 2.3.0
- `diffusers >= 0.30.0` required — earlier versions import `cached_download` which was removed in huggingface_hub 0.24+
- Docker images on VM 131 are not persistent across daemon restarts — rebuild with `build-job.sh` if the image goes missing

---

## WebUI

Image generation on VM 101 (portainer, `192.168.x.5`).

- **Port:** 7860
- **External URL:** http://stable.yourdomain.com
- **GPU:** RTX A2000 12GB (passed through at Proxmox level — not in compose)
- **Image:** `sd-auto:local` (locally built image)

## Deployment

The compose file uses a locally built image (`sd-auto:local`). You must build before deploying:

```bash
# 1. Build the image on VM 101 (takes 15–30 min on first run)
./build.sh

# 2. Start the container
./deploy.sh
```

`build.sh` copies the Dockerfile to VM 101 and runs `docker build` there. Re-run it whenever the Dockerfile changes.

## Fork note

The Dockerfile clones `comp6062/Stability-AI-stablediffusion` (a community mirror) instead of the official `Stability-AI/stablediffusion`. The official repo requires a Hugging Face access agreement and login to clone — the mirror removes that gate so the build works without credentials.

## Data paths

| Path on host | Purpose |
|---|---|
| `/mnt/media/stable-diffusion/models` | Checkpoints and models |
| `/mnt/media/stable-diffusion/embeddings` | Textual inversions |
| `/mnt/media/stable-diffusion/outputs` | Generated images |
| `/mnt/media/stable-diffusion/Lora` | LoRA weights |
| `/mnt/media/stable-diffusion/VAE` | VAE models |

## Environment variables

| Variable | Description |
|---|---|
| `CLI_ARGS` | Extra launch arguments passed to the WebUI (e.g. `--xformers`) |
| `NVIDIA_VISIBLE_DEVICES` | GPU visibility (default: `all`) |
| `NVIDIA_DRIVER_CAPABILITIES` | Driver capabilities (default: `all`) |

## Launch flags (hardcoded in CMD)

| Flag | Description |
|---|---|
| `--no-half-vae` | Prevents VAE color shift artifacts on cards with limited VRAM (required for RTX A2000 12GB) |
| `--xformers` | Memory-efficient attention — reduces VRAM usage significantly |
| `--api` | Enables the REST API endpoint at `/sdapi/v1/` |
