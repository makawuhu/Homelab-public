# autoforge-ui

Web UI for the AutoForge 3MF generation pipeline. Manages HueForge projects, triggers 2-pass AI-assisted rendering on vast.ai GPU instances, and produces print-ready `.3mf` files for BambuStudio.

- **Host:** VM 101 (`192.168.x.5`)
- **Port:** 8055
- **External URL:** https://autoforge.yourdomain.com

## What it does

1. Lists HueForge projects from `/mnt/media/claude/hueforge`
2. Lets you pick filament colors from the local filament library (`my-filaments.json`)
3. Spins up a vast.ai GPU instance via API
4. Runs the 2-pass AutoForge pipeline (pass 1 → STL, pass 2 → sliced 3MF)
5. Returns a downloadable `.3mf` file with BambuStudio-compatible slicer settings

## Volumes

| Host path | Container path | Purpose |
|-----------|----------------|---------|
| `/mnt/media/claude/hueforge` | `/data/hueforge` | HueForge project files, STL outputs, filament library |
| `/root/.secrets/autoforge-ssh-key` | `/run/secrets/vastai-ssh-key` | SSH key for vast.ai instance access |

## Environment variables

| Variable | Description |
|----------|-------------|
| `VASTAI_API_KEY` | vast.ai API key — used to create/manage GPU instances |
| `HUEFORGE_BASE` | Base path for HueForge projects (default: `/data/hueforge`) |
| `TRUCK_REF_PATH` | Reference 3MF used as slicer settings template |

## Deploy

Managed via GitOps. The image is built locally from the `app/` directory (FastAPI + Python).

```bash
docker compose -f services/autoforge-ui/compose.yml up -d --build
```

## Notes

- vast.ai instances are **paused** (not destroyed) after jobs complete — disk is preserved
- The `make_3mf.py` module handles BambuStudio 3MF assembly (JSON keys, infill enums, profile inheritance)
- See `feedback_vastai_stop.md` in memory: never destroy instances after jobs
