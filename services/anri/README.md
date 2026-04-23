# Anri — Personal Operations Agent

**Agent:** Anri (named after the Shining Force hero)
**Role:** Personal agent for creative, trading, and research workflows
**CT:** 129 | **IP:** 192.168.x.165 | **OpenClaw version:** 2026.4.10

## Purpose

Anri handles Matt's day-to-day creative and research work — Stable Diffusion image generation, trading data lookups, fun facts, and general personal assistant tasks. Anri does **not** manage homelab infrastructure (that's Khris's domain).

## Architecture

```
┌─────────────────────────────────────────┐
│                 Anri                     │
│  CT 129 · 192.168.x.165                │
│  OpenClaw 2026.4.10 · GLM 5.1:cloud     │
├─────────────────────────────────────────┤
│  Channels: Telegram, Discord (Anri-Bot) │
│  Gateway: port 18789, bind=lan          │
│  Plugins: Brave search, Ollama, Honcho  │
│  Tools: SD (stable.yourdomain.com),       │
│         Options Desk (.5:8010)          │
├─────────────────────────────────────────┤
│  Workspace: Images, daily facts,        │
│  creative projects                      │
└─────────────────────────────────────────┘
```

## Model Config

| Field | Value |
|-------|-------|
| Primary | `ollama/glm-5.1:cloud` |
| Compaction | safeguard mode |
| Context window | 202,752 tokens |
| Max output | 8,192 tokens |

Also has access to Anthropic Claude models (sonnet-4, haiku-4) and local Ollama models (qwen3:14b, deepseek-r1:14b, mistral:7b, etc.) for escalation.

## Channels

| Channel | Bot/Handle | ID |
|---------|-----------|-----|
| Telegram | @yourhostnameanribot | token: 8618…zgNc |
| Discord | Anri-Bot | 1494544485215109120 |

- Guild: mattbeau's server (1494499805039431710)
- Policy: allowlist, requireMention=false

## LXC Spec

| Field | Value |
|-------|-------|
| CT ID | 129 |
| Hostname | anri |
| CPU cores | 8 |
| RAM | 16,384 MB (16 GB) |
| Swap | (default) |
| Storage | 128 GB (local-zfs) |
| Network | bridge=vmbr0, static 192.168.x.165/24 |
| DNS | 192.168.x.1 (OPNsense) |
| Features | nesting=1, keyctl=1 |
| Boot | On boot: yes |

## DNS & Proxy

| Record | Target | Proxy ID |
|--------|--------|----------|
| anri.yourdomain.com | 192.168.x.31 → 192.168.x.165:18789 | 91 |

- NPM cert_id: 2 (*.yourdomain.com wildcard)
- HSTS: no, HTTP/2: yes, WebSockets: not configured

## Scope & Boundaries

- **Owns:** Creative workflows, SD generation, trading data research, personal assistant tasks
- **Does NOT:** Manage infrastructure, enforce deployment gates, or touch production systems
- **Escalates to:** Claude Sonnet for complex reasoning or high-stakes decisions

## Tools

| Tool | Purpose |
|------|---------|
| Stable Diffusion | Image generation (stable.yourdomain.com, A1111 API) |
| Options Desk | Trading data lookups (192.168.x.5:8010) |
| Brave Search | Web research |
| Honcho | Memory plugin (192.168.x.5:8050, workspace: anri) |
| Telegram | Notifications to Matt |

## Key Files

| Path | Purpose |
|------|---------|
| `/root/.openclaw/workspace/SOUL.md` | Agent persona — creative/trading focus |
| `/root/.openclaw/workspace/IDENTITY.md` | Name: Anri, emoji: 🎯 |
| `/root/.openclaw/workspace/TOOLS.md` | SD settings, API endpoints |
| `/root/.openclaw/openclaw.json` | Channel configs, model list, plugins |

## Rollback

1. Stop OpenClaw gateway on CT 129
2. `pct stop 129 && pct destroy 129`
3. Remove DNS entry anri.yourdomain.com
4. Remove NPM proxy host (ID 91)
5. Delete Telegram bot (@yourhostnameanribot)
6. Delete Discord bot (Anri-Bot)