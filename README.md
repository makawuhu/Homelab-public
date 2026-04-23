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
| `192.168.x.51` | CT 125 — `ollama` | Ollama LLM API (CT, ollama moved to VM 101:11434) |
| `192.168.x.8` | CT 102 — `claude-ops` | GitOps controller + deploy webhook |
| `192.168.x.165` | CT 129 — `anri` | Anri personal agent (creative/trading/research) |
| `192.168.x.167` | VM 131 — `gpu` | GPU API (RTX 4070 Super) + depth estimation |
| `192.168.x.168` | CT 132 — `studio` | Studio (3D design) |
| `192.168.x.169` | CT 133 — `tao` | Tao homelab information operator |
| `192.168.x.171` | CT 135 — `max` | Max OpenCode agent (ChatGPT) — CLI-only |

## Services

| Service | URL | Host |
|---------|-----|------|
| Homepage | https://homepage.yourdomain.com | VM 101 :3005 |
| Gitea | https://gitea.yourdomain.com | CT 123 :3010 |
| Portainer | https://portainer.yourdomain.com | VM 101 :9443 |
| Uptime Kuma | https://status.yourdomain.com | VM 101 :3001 |
| Beszel | https://beszel.yourdomain.com | VM 101 :8091 |
| Wazuh | https://wazuh.yourdomain.com | CT 122 :8443 |
| Jellyfin | https://jellyfin.yourdomain.com | VM 101 :8096 |
| Immich | https://immich.yourdomain.com | VM 101 :2283 |
| Stable Diffusion | https://stable.yourdomain.com | VM 101 :7860 |
| Ollama | http://ollama.yourdomain.com | VM 101 :11434 |
| FileBrowser | http://filebrowser.yourdomain.com | VM 101 :8080 |
| Dozzle | https://dozzle.yourdomain.com | VM 101 :8888 |
| CoolerControl | https://coolercontrol.yourdomain.com | VM 101 |
| Honcho | https://honcho.yourdomain.com | VM 101 :8050 |
| AutoForge UI | https://autoforge.yourdomain.com | VM 101 :8055 |
| OPC | https://opc.yourdomain.com | VM 101 :5173 |
| GPU API | https://gpu.yourdomain.com | VM 131 :8000 |
| GPU Outputs | https://gpu-outputs.yourdomain.com | VM 131 :8001 |
| Studio | https://studio.yourdomain.com | CT 132 |
| Tao | https://tao.yourdomain.com | CT 133 |
| Anri | https://anri.yourdomain.com | CT 129 (personal agent, Khris-managed) |
| Max | — | CT 135 (OpenCode agent, CLI-only) |
| NPM | http://nginx.yourdomain.com | CT 104 :81 |
| Proxmox | http://proxmox.yourdomain.com | 192.168.x.4 :8006 |

## Repo Structure

```
services/
  authelia/            Authelia SSO/2FA (CT 124, stopped)
  autoforge-ui/        AutoForge 3MF pipeline UI (VM 101 :8055)
  beszel/              System monitor (VM 101 :8091)
  coolercontrol/       Fan control daemon (VM 101)
  dozzle/              Docker log viewer (VM 101 :8888)
  filebrowser/         FileBrowser (VM 101 :8080)
  gitea/               Gitea git server + Postgres (CT 123 :3010)
  gpu/                 GPU API + depth estimation (VM 131)
  homepage/            Homepage dashboard (VM 101 :3005)
  honcho/              Honcho memory service (VM 101 :8050)
  immich/              Photo & video backup (VM 101 :2283)
  jellyfin/            Media server (VM 101 :8096)
  ollama/              Ollama LLM API (VM 101 :11434)
  opc/                 Options trading platform (VM 101 :5173)
  portainer/           Portainer CE (VM 101 :9443)
  stable-diffusion/    Stable Diffusion WebUI (VM 101 :7860)
  studio/             Studio 3D design (CT 132)
  anri/               Anri personal agent (CT 129)
  tao/                 Tao homelab info operator (CT 133)
  max/                 Max OpenCode agent (CT 135)
  uptime-kuma/         Uptime monitor (VM 101 :3001)
  wazuh/               Wazuh SIEM/XDR (CT 122 :8443)
  webhook/             Deploy webhook pipeline (CT 102 :9000)

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