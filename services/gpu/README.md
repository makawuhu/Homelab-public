# GPU Compute Service

Serverless-style GPU compute for the yourhostname homelab.

- **Host:** VM 131 (`192.168.x.167`)
- **API Port:** 8080 (proxied via NPM)
- **Swagger Docs:** https://gpu.yourdomain.com/docs
- **Outputs:** https://gpu-outputs.yourdomain.com
- **Hardware:** RTX 4070 Super, 12GB VRAM, CUDA 13.0

## Architecture

```
Studio (studio.yourdomain.com)  →  POST /jobs  →  GPU API (gpu.yourdomain.com)
                              ←  GET /jobs/{id}  ←  (polls every 3s)
Result: gpu-outputs.yourdomain.com/{filename}
```

## Stack

- **API:** FastAPI (Python 3.12) — job submission, status, queue, models
- **Worker:** BullMQ-compatible Docker job runner (gpu-worker:latest)
- **Redis:** Job queue backend
- **File Server:** Serves generated images from /opt/outputs
- **Models:** /opt/models (SD checkpoints, mounted read-only)

## Job Types

| Type | Description |
|------|-------------|
| `custom_docker` | Run any Docker container with GPU access |
| `autoforge` | AutoForge pipeline worker |
| `benchmark` | GPU stats snapshot |
| `image_generation` | Reserved for direct SD generation |
| `ml_inference` | Reserved for ML inference |

## NPM Proxies

- ID 94: gpu.yourdomain.com → 192.168.x.167:8080
- ID 95: gpu-outputs.yourdomain.com → 192.168.x.167:8081

## Deployment

```bash
cd /opt/gpu-compute
docker compose up -d
```

API hot-reloads on file change (volume-mounted). For version bumps, restart:
```bash
docker restart gpu-api
```