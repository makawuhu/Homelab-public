# homelab

GitOps source of truth for a Proxmox-based homelab running on a Dell Precision 7820. Everything from infrastructure configuration to service compose files lives here.

## Hardware

| Component | Detail |
|-----------|--------|
| Host | Dell Precision 7820 Workstation |
| CPU | Intel Xeon Gold 6248 — 40 threads (1 socket, 20c HT) |
| RAM | 187 GB DDR4 ECC |
| GPU 0 | NVIDIA RTX 4070 SUPER — `0000:17:00` (VM 131, GPU workloads) |
| GPU 1 | NVIDIA RTX A2000 12GB — `0000:65:00` (VM 134, AI workloads) |
| Storage | 512 GB SSD (OS/ZFS) · 1.92 TB SSD (VMs) · 4 TB HDD (media) · 2 TB NVMe |
| Hypervisor | Proxmox VE |

## Network

All services are **LAN-only**. Remote access via Tailscale on OPNsense. DNS is handled by OPNsense Unbound → Nginx Proxy Manager (CT 104).

| IP | Host | Role |
|----|------|------|
| `192.168.x.1` | OPNsense | Firewall / router |
| `192.168.x.4` | Proxmox VE | Hypervisor |
| `192.168.x.5` | VM 101 — `portainer` | Primary Docker host |
| `192.168.x.31` | CT 104 — `nginxproxymanager` | Reverse proxy + SSL |
| `192.168.x.47` | CT 122 — `wazuh` | Wazuh SIEM/XDR |
| `192.168.x.48` | CT 123 — `gitea` | Gitea git server + Postgres |
| `192.168.x.51` | CT 125 — `ollama` | Ollama LXC (service deployed to VM 101 :11434) |
| `192.168.x.8` | CT 102 — `claude-ops` | GitOps controller + deploy webhook |
| `192.168.x.163` | CT 103 — `khris` | Khris — Hermes Agent bot (Telegram) |
| `192.168.x.165` | CT 129 — `anri` | Anri personal agent (creative/trading/research) |
| `192.168.x.167` | VM 131 — `gpu` | GPU API (RTX 4070 Super) + depth estimation |
| `192.168.x.168` | CT 132 — `studio` | Studio (3D design) |
| `192.168.x.169` | CT 133 — `tao` | Tao homelab information operator |
| `192.168.x.171` | CT 135 — `max` | Max OpenCode agent (ChatGPT) — CLI-only |

## Services

<!-- gen:services -->
| Service | URL | Host |
|---------|-----|------|
| Anri | https://anri.yourdomain.com | CT 129 |
| Ash | https://ash.yourdomain.com | CT 136 |
| AutoForge UI | https://autoforge.yourdomain.com | VM 101 |
| Beszel | https://beszel.yourdomain.com | VM 101 |
| Dozzle | https://dozzle.yourdomain.com | VM 101 |
| FileBrowser | http://filebrowser.yourdomain.com | VM 101 |
| Gitea | https://gitea.yourdomain.com | CT 123 |
| GPU API | https://gpu.yourdomain.com | VM 131 |
| Homepage | https://homepage.yourdomain.com | VM 101 |
| Honcho | https://honcho.yourdomain.com | VM 101 |
| Immich | https://immich.yourdomain.com | VM 101 |
| Jellyfin | https://jellyfin.yourdomain.com | VM 101 |
| Nature-Forge UI | https://nature-forge.yourdomain.com | VM 101 |
| Ollama | http://ollama.yourdomain.com | VM 101 |
| OPC | https://opc.yourdomain.com | VM 101 |
| Portainer | https://portainer.yourdomain.com | VM 101 |
| Stable Diffusion | http://stable.yourdomain.com | VM 134 |
| Studio | https://studio.yourdomain.com | CT 132 |
| Tao | https://tao.yourdomain.com | CT 133 |
| Uptime Kuma | https://status.yourdomain.com | VM 101 |
| Wazuh | https://wazuh.yourdomain.com | CT 122 |
<!-- /gen:services -->

## Repo Structure

<!-- gen:repo-structure -->
```
services/
  ai/                     VM 134 (192.168.x.170)
  anri/                   CT 129 (192.168.x.165)
  ash/                    CT 136 (192.168.x.172)
  autoforge-ui/           3MF slicer UI + RunPod/vast.ai GPU integration on VM 101
  beszel/                 Monitoring hub on VM 101
  claude-ops/             CT 102 (192.168.x.8) — GitOps controller node
  coolercontrol/          Privileged container for fan/cooling control on VM 101
  dozzle/                 Read-only docker.sock access
  filebrowser/            Serves /mnt/media on VM 101 as uid=1000
  gitea/                  GitOps source of truth on CT 123 — loss is catastrophic
  gpu/                    GPU compute API on VM 131 (RTX 4070 Super)
  homelab-assistant/      Placeholder directory
  homepage/               Config in-repo at services/homepage/config
  honcho/                 Builds from plastic-labs/honcho (GitHub) cloned to /opt/honcho on VM 101
  immich/                 Photo library on 4TB HDD
  jellyfin/               Media library on 4TB HDD at /mnt/media
  khris/                  CT 103 (192.168.x.163)
  max/                    CT 135 (192.168.x.171)
  nature-forge-ui/        Built from local Dockerfile
  ollama/                 Ollama LLM inference on VM 101
  ollama-gpu/             Ollama on VM 134 (RTX A2000)
  opc/                    Options trading platform on VM 101
  portainer/              Docker management UI on VM 101
  renovate/               One-shot job on CT 102 (no restart policy)
  stable-diffusion/       A1111 Stable Diffusion on VM 134 (RTX A2000)
  studio/                 Stable Diffusion UI on CT 132 (192.168.x.168)
  tao/                    CT 133 (192.168.x.169)
  uptime-kuma/            Uptime monitoring on VM 101
  wazuh/                  SIEM/XDR on CT 122
  webhook/                Critical GitOps infrastructure on CT 102 (this node)

network/               Network configs (NPM, OPNsense, iperf3)
proxmox/               Host docs — hardware, ZFS, GPU passthrough, backups
vms/                   VM-specific docs
auth/                  Auth / SSO overview
docs/                  DR procedure, pipeline docs
scripts/               Utility scripts (inventory.sh, deploy-all.sh, sanitize-push.sh)
secrets/               SOPS-encrypted secrets (never plaintext)

.gitea/
  workflows/ci.yml     CI — conventional commit linting on every PR
  RUNNER_SETUP.md      Gitea Actions runner setup guide
```
<!-- /gen:repo-structure -->

## How Deploys Work

### Automatic (GitOps)

Merging a PR to `main` triggers the deploy webhook on CT 102 (`http://192.168.x.8:9000/hooks/webhook-handler`). The webhook script detects which `services/` paths changed and for each changed service with a `.deploy` file: SSHs to the target host, pulls the repo, and runs `docker compose up -d`.

Services declare their target host in a `.deploy` file:
```
HOST=192.168.x.5
```

For services on CT 102 (the webhook host itself), deploy runs locally without SSH.

### Manual

Each service directory has a `deploy.sh` that SSHs to the target host:

```bash
cd services/gitea
./deploy.sh
```

Manual deploys can be run from CT 102 (claude-ops), which has SSH key access to all hosts.

## CI Pipeline

Gitea Actions CI runs on every PR to `main` or `dev` via a self-hosted runner on CT 123.

**Workflow:** `.gitea/workflows/ci.yml`
- **Conventional commits** — all commit messages must follow `type(scope): description` format
- Allowed types: `feat`, `fix`, `docs`, `refactor`, `chore`, `test`, `perf`
- Merge commits are exempt

See `.gitea/RUNNER_SETUP.md` for runner provisioning and troubleshooting.

## Operations Node

**Primary: Claude** (CT 102, `192.168.x.8`) is the GitOps controller. Owns deployments, architecture, and code. Runs the deploy webhook on port 9000.

## Secrets Policy

- Never commit `.env` files — only `.env.example` (placeholders) and `.env.sops` (SOPS-encrypted)
- All secrets are encrypted with [SOPS + age](https://github.com/getsops/sops) and stored in `secrets/`
- The age private key lives at `/root/.age/key.txt` on CT 102 — never commit it
- `deploy.sh` auto-decrypts `.env.sops` → `.env` on the target host before `docker compose up`
- See `docs/DR.md` for the full recovery procedure

## Related Repos

- [Ollama-Model-Manager](https://github.com/yourhostname/Ollama-Model-Manager)
- [proxmox-vm-controller](https://github.com/yourhostname/proxmox-vm-controller)
- [homelab-public](https://github.com/yourhostname/homelab-public) — sanitized public mirror of this repo

## Roadmap

See [`ROADMAP.md`](./ROADMAP.md) for full task tracking.