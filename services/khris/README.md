# Khris — Primary Ops Agent

**Agent:** Khris (named after the Shining Force priest)
**Role:** Primary operations agent for the yourhostname homelab — deployments, container lifecycle, DNS/proxy, infra health, routine maintenance
**CT:** 103 | **IP:** 192.168.x.163 | **OpenClaw version:** 2026.4.9 (0512059)

## Purpose

Khris is the homelab's primary ops agent. It owns GitOps deployments, container lifecycle, DNS/NPM management, health monitoring, and infrastructure maintenance. It operates under a three-gate deployment process (Plan → PR → Execute with explicit approval).

## Architecture

```
┌─────────────────────────────────────────┐
│                 Khris                    │
│  CT 103 · 192.168.x.163                │
│  OpenClaw 2026.4.9 · GLM 5.1:cloud      │
├─────────────────────────────────────────┤
│  Channels: Telegram, Discord (Khris-Bot)│
│  Gateway: port 18789, bind=loopback     │
│  Plugins: Brave, Ollama, Anthropic      │
├─────────────────────────────────────────┤
│  Services on this CT:                   │
│  - OpenClaw gateway (system process)    │
│  - Authentik (SSO) — Docker stack      │
│  - NPM (sandbox)                        │
│  - Gitea (sandbox)                      │
│  - Uptime Kuma, Dozzle, FileBrowser    │
│  - Beszel agent                         │
│  - webhook-prod (stopped)               │
│  - Renovate (cron, not running)         │
└─────────────────────────────────────────┘
```

## Model Config

| Field | Value |
|-------|-------|
| Primary | `ollama/glm-5.1:cloud` |
| Compaction | (default — not explicitly set) |
| Context window | 202,752 tokens |
| Max output | 8,192 tokens |

## Channels

| Channel | Bot | ID |
|---------|-----|----|
| Telegram | (bot token 8623…MCrI) | — |
| Discord | Khris-Bot | 1494501045760430110 |

- Guild: mattbeau's server (1494499805039431710)
- Policy: allowlist, requireMention=false, allowBots=true

## LXC Spec

| Field | Value |
|-------|-------|
| CT ID | 103 |
| Hostname | khris |
| CPU cores | 4 |
| RAM | 16,384 MB (16 GB) |
| Swap | (default) |
| Storage | 128 GB (local-zfs) |
| Network | bridge=vmbr0, DHCP |
| DNS | 192.168.x.1 (OPNsense) |
| Features | nesting=1, keyctl=1 |
| Boot | On boot: no |

## DNS & Proxy

No NPM proxy or DNS entry. Khris connects outbound to Discord/Telegram APIs — no inbound access required.

## Scope & Boundaries

- **Owns:** Deployments, container lifecycle, DNS/proxy, health checks, GitOps pipeline
- **Full root SSH:** All production hosts for deployment, monitoring, and maintenance
- **Scope limit:** Writes restricted to khris-* resources; other hosts monitored only unless explicitly authorized
- **Three-gate process:** All deployments require Plan → PR → explicit "proceed" from Matt
- **Escalation:** Multi-step ambiguous infra state → stronger model; routine checks stay local

## Tools

| Tool | Access | Scope |
|------|--------|-------|
| Proxmox API | khris@pve!ct103 token | Create/manage LXCs with khris- prefix |
| NPM | khris@yourdomain.com user | khris-* subdomain proxies only |
| Gitea | your-gitea-user/homelab (write) | Production GitOps repo |
| OPNsense DNS | API via SOPS-encrypted creds | New service DNS entries |
| SSH | root on all infra CTs/VMs | Full access for deploy; writes scoped to khris-* resources |

## Key Files

| Path | Purpose |
|------|---------|
| `/root/.openclaw/workspace/SOUL.md` | Agent persona and operational rules |
| `/root/.openclaw/workspace/USER.md` | Matt context and preferences |
| `/root/.openclaw/workspace/MEMORY.md` | Long-term memory (curated) |
| `/root/.openclaw/workspace/TOOLS.md` | Infrastructure cheat sheet |
| `/root/.openclaw/workspace/HEARTBEAT.md` | Periodic check tasks |
| `/root/.openclaw/workspace/IDENTITY.md` | Name, emoji, avatar |
| `/root/.openclaw/openclaw.json` | Agent config (channels, models, plugins) |
| `/opt/homelab/` | GitOps repo (auto-synced via webhook) |

## Related Services

- **webhook-prod** — GitOps deploy pipeline (port 9001, currently stopped)
- **Authentik** — SSO (Docker stack: server, worker, postgresql, redis)
- **Renovate** — Dependency update bot (weekly cron, currently exited)
- **NPM** — Sandbox Nginx Proxy Manager
- **Gitea** — Sandbox Gitea (port 3010)
- **Uptime Kuma** — Uptime monitor (port 3001)
- **Dozzle** — Docker log viewer (port 8888)
- **FileBrowser** — File manager (port 8080)
- **Beszel agent** — Monitoring agent (port 991)

## Rollback

1. Stop OpenClaw gateway on CT 103
2. Destroy CT 103 (removes all services on it, including webhook-prod and Authentik)
3. Remove DNS entry if public proxy exists
4. Remove Discord bot
5. **Warning:** CT 103 hosts the GitOps deploy pipeline — destroying it breaks all automated deployments