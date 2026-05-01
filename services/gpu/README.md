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

---

## Dev Workflow (nature-forge-dev)

A dev-only profile service for iterating on Nature-Forge parameters directly on the GPU host.
Not started by the standard GitOps deploy — must be activated explicitly with `--profile dev`.

### Prerequisites (one-time, manual on VM 131)

```bash
mkdir -p /opt/nature-forge-dev/input /opt/nature-forge-dev/output
cp /path/to/truckee-tahoe.png /opt/nature-forge-dev/input/
```

### job.json template

Save as `/opt/nature-forge-dev/job.json`:

```json
{
  "input_image": "/workspace/input/truckee-tahoe.png",
  "preset": "polymaker-photo-bw",
  "cli_args": {
    "width": 150,
    "layer_height": 0.08,
    "base_layer": 8,
    "blend_depth": 31,
    "detail_size": 0.2,
    "pruning_max_swaps": 6
  }
}
```

`base_layer` is a layer count; at `layer_height: 0.08` this gives a 0.64mm base (8 × 0.08mm minimum safe base).

### Run command

```bash
docker compose --profile dev -f /opt/gpu-compute/docker-compose.yml run --rm nature-forge-dev
```

Outputs land in `/opt/nature-forge-dev/output/`. Check result:

```bash
cat /opt/nature-forge-dev/output/result.json | python3 -m json.tool | grep -E "status|returncode"
```

### GPU contention warning

VM 131 is the production GPU host for Studio. Do not run the dev container while the GPU queue is active.

Verify first:

```bash
curl -s https://gpu.yourdomain.com/health | python3 -m json.tool
```

Proceed only when `workers_active=0` and `queue_depth=0`.

### Rollback

Stop any stuck dev run:

```bash
docker stop nature-forge-dev 2>/dev/null || true
```

Then remove the `nature-forge-dev` service block from `services/gpu/compose.yml` and merge the reverting PR.
The webhook will SCP the updated file to `/opt/gpu-compute/docker-compose.yml` and run `docker compose up -d --remove-orphans`.
No production service is affected.

### Image updates

`nature-forge-worker:local` is built manually on VM 131 from `/opt/nature-forge/`:

```bash
docker build -t nature-forge-worker:local /opt/nature-forge/
```