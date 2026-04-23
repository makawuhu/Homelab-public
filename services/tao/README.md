# Tao — Homelab Information Operator

**Agent:** Tao (named after the Shining Force wizard)
**Role:** Information operator — reads and answers questions about homelab infrastructure, services, configs, and deployment history
**CT:** 133 | **IP:** 192.168.x.169 | **OpenClaw version:** 2026.4.15

## Purpose

Tao serves as a shared knowledge base that any agent (Khris, Lowe, Anri) or Matt can query for homelab facts — IPs, service configs, DNS entries, deploy procedures, and infrastructure state. Instead of each agent maintaining its own mental model, Tao indexes the single source of truth (the `your-gitea-user/homelab` repo) and provides authoritative answers.

## Architecture

```
┌─────────────────────────────────────────┐
│                 Tao                      │
│  CT 133 · 192.168.x.169                │
│  OpenClaw 2026.4.15 · GLM 5.1:cloud     │
├─────────────────────────────────────────┤
│  Channels: Discord (Tao-Bot)           │
│  Gateway: port 18789, bind=lan          │
│  Plugins: Brave search, Ollama          │
├─────────────────────────────────────────┤
│  Knowledge: your-gitea-user/homelab repo  │
│  (read-only, cloned at /root/homelab)   │
└─────────────────────────────────────────┘
```

## Model Config

| Field | Value |
|-------|-------|
| Primary | `ollama/glm-5.1:cloud` |
| Fallback | `ollama/minimax-m2.7:cloud` |
| Compaction | safeguard mode |
| Context window | 202,752 tokens |
| Max output | 8,192 tokens |

## Channels

| Channel | Bot | ID |
|---------|-----|----|
| Discord | Tao-Bot | 1494819074012872835 |

- Guild: mattbeau's server (1494499805039431710)
- Policy: allowlist, requireMention=false, allowBots=true
- No Telegram access

## LXC Spec

| Field | Value |
|-------|-------|
| CT ID | 133 |
| Hostname | tao |
| CPU cores | 2 |
| RAM | 4,096 MB (4 GB) |
| Swap | (default) |
| Storage | 32 GB (vmpool) |
| Network | bridge=vmbr0, DHCP |
| DNS | 192.168.x.1 (OPNsense) |
| Features | nesting=1, keyctl=1 |
| Boot | On boot: yes |

## DNS & Proxy

| Record | Target | Proxy ID |
|--------|--------|----------|
| tao.yourdomain.com | 192.168.x.31 → 192.168.x.169:18789 | 90 |

- NPM cert_id: 2 (*.yourdomain.com wildcard)
- HSTS: yes, HTTP/2: yes, WebSockets: not configured

**⚠️ DNS issue:** tao.yourdomain.com has two A records in OPNsense — one pointing to 192.168.x.169 (direct) and one to 192.168.x.31 (NPM). Per convention, only the .31 entry should exist (NPM handles routing). The direct .169 entry should be removed.

## Scope & Boundaries

- **Owns:** Answering questions about homelab infrastructure
- **Does NOT:** Modify the homelab repo, deploy services, expose SOPS secrets, or make infra changes
- **Knowledge source:** `your-gitea-user/homelab` repo (read-only, cloned at `/root/homelab`)
- **Citations:** Always cite file paths and line numbers when referencing configs

## Tools

| Tool | Purpose |
|------|---------|
| Brave Search | Web lookups when needed |
| Homelab repo | Primary knowledge source (/root/homelab) |
| Gateway API | Other agents can query Tao via POST to http://192.168.x.169:18789 |

## Key Files

| Path | Purpose |
|------|---------|
| `/root/.openclaw/workspace/SOUL.md` | Agent persona — information operator |
| `/root/.openclaw/workspace/IDENTITY.md` | Name: Tao, emoji: 📖 |
| `/root/.openclaw/workspace/AGENTS.md` | Session startup, memory hygiene rules |
| `/root/homelab/` | Cloned your-gitea-user/homelab (read-only) |

## Rollback

1. Stop OpenClaw gateway on CT 133
2. `pct stop 133 && pct destroy 133`
3. Remove DNS entry tao.yourdomain.com
4. Remove NPM proxy host (ID 90)
5. Delete Discord bot (Tao-Bot)