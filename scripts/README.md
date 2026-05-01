# Scripts

Utility scripts for the homelab GitOps repo. Run from claude-ops (`192.168.x.8`).

## inventory.sh

Queries Proxmox via SSH and prints a live snapshot of all LXCs, VMs, and ZFS pool status.

```bash
bash scripts/inventory.sh
```

Output includes: VMID, name, status, and memory usage for each LXC/VM.

## new-service.sh

Scaffolds a new service folder and wires up DNS, reverse proxy, and monitoring in one step.

```bash
# Full setup — creates files, DNS, NPM proxy, Uptime Kuma monitor, updates CLAUDE.md
bash scripts/new-service.sh myapp --port 9000

# Custom host / HTTP-only
bash scripts/new-service.sh myapp --port 9000 --host 192.168.x.8 --scheme http

# LAN-only (skip DNS + NPM + monitor)
bash scripts/new-service.sh myapp --port 9000 --no-proxy --no-monitor
```

**What it creates:**
- `services/<name>/README.md` — pre-filled with host, port, and URL
- `services/<name>/compose.yml` — skeleton with TODOs for image and container port
- `services/<name>/.env.example` — empty, ready to populate
- `services/<name>/deploy.sh` — deploy script for the target host

**What it wires up:**
- OPNsense Unbound DNS override: `<name>.yourdomain.com → 192.168.x.31`
- NPM proxy host with wildcard cert (cert ID 2)
- Uptime Kuma HTTP monitor on `http://<host>:<port>`
- Entry in CLAUDE.md repo structure and URL table

**Pre-flight conflict check:** Before creating the NPM proxy, the script checks for conflicts in two places — the NPM database AND stale `.conf` files on the NPM host disk (left behind when entries are deleted from the DB without nginx cleanup). Both prompt for auto-delete before proceeding.

## deploy-all.sh

Runs `deploy.sh` for a curated subset of services that support idempotent redeployment.

```bash
bash scripts/deploy-all.sh
```

**Covered:** nginxproxymanager, portainer

**Not covered (intentional):**
- VM 101 Docker services (jellyfin, openwebui, ollama, stable-diffusion, filebrowser, uptime-kuma, coolercontrol, watchtower) — deployed directly on portainer VM, not managed from here
- monitoring — Portainer git-backed stack; redeploy via Portainer API or UI
- homelab-assistant — deployed on this LXC; run `services/homelab-assistant/deploy.sh` directly
