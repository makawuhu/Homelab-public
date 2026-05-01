# Khris — Hermes Agent Bot

**Agent:** Khris
**Framework:** Hermes Agent v0.11.0 (NousResearch)
**CT:** 103 | **IP:** 192.168.x.163

## Architecture

```
┌─────────────────────────────────────────┐
│                 Khris                    │
│  CT 103 · 192.168.x.163                │
│  Hermes Agent v0.11.0 · gpt-5.5         │
├─────────────────────────────────────────┤
│  Channels: Discord                      │
│  Model: ChatGPT Codex 5.5 (cloud)       │
│  Codex CLI 0.125.0 (local)              │
└─────────────────────────────────────────┘
```

## Model Config

| Field | Value |
|-------|-------|
| Provider | `openai-codex` |
| Model | `gpt-5.5` |
| Base URL | `https://chatgpt.com/backend-api/codex` |
| Codex CLI | v0.125.0 at `/usr/local/bin/codex` |

## Channels

| Channel | Mode |
|---------|------|
| Discord | Bot token in `.env` · allowed user: `546870673956667393` · home channel: `1498535295749197946` |

## LXC Spec

| Field | Value |
|-------|-------|
| CT ID | 103 |
| Hostname | khris |
| CPU cores | 8 |
| RAM | 16,384 MB (16 GB) |
| Swap | 512 MB |
| Storage | 128 GB (local-zfs) |
| Network | bridge=vmbr0, ip=192.168.x.163/24, gw=192.168.x.1 |
| DNS | 192.168.x.1 (OPNsense) |
| Features | nesting=1, keyctl=1 |
| Boot | On boot: yes |

## DNS & Proxy

None — hermes runs in Telegram polling mode (outbound only, no inbound port).

## Khris Repo

Tools and scripts for Khris live at **https://github.com/yourhostname/khris** (private).

Khris can provision services under its own namespace using:

| Command | Effect |
|---------|--------|
| `khris-provision <name> <host> <port> [scheme]` | DNS + NPM in one shot |
| `khris-npm-add <name> <host> <port> [scheme]` | NPM proxy host `khris-<name>.yourdomain.com` |
| `khris-dns-add <name>` | Unbound override `khris-<name>.yourdomain.com → 192.168.x.31` |

Scripts are installed at `/usr/local/bin/` on CT 103. Credentials at `/etc/khris/env`.

## Key Files

| Path | Purpose |
|------|---------|
| `~/.hermes/config.yaml` | Model and terminal config |
| `~/.hermes/.env` | Telegram bot token, access policy |
| `~/.hermes/logs/agent.log` | Agent session logs |
| `~/.hermes/logs/errors.log` | Error log |
| `/etc/systemd/system/hermes.service` | Systemd unit (auto-start) |

## Service Management

```bash
systemctl status hermes
systemctl restart hermes
journalctl -u hermes -f
tail -f ~/.hermes/logs/agent.log
```
