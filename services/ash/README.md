# Ash

**CT:** 136 | **IP:** 192.168.x.172 | **Hermes Agent version:** v0.11.0

Ash is a Hermes Agent bot that plays Pokemon Blue autonomously via headless PyBoy emulation. It uses the bundled `gaming/pokemon-player` skill, connects to a local game server on port 9876, and can be directed via Telegram.

**Dashboard:** https://ash.yourdomain.com/dashboard/ — live screenshot feed, game state, action log.

## Stack

| Component | Detail |
|-----------|--------|
| Agent | Hermes Agent v0.11.0 |
| Model | gpt-5.5 via openai-codex (context 272k) |
| Channel | Telegram (allowed user: Matthew) |
| Emulator | PyBoy (via pokemon-agent) |
| Game | Pokemon Blue |
| Game server | localhost:9876, proxied at ash.yourdomain.com |

## Config files

| Path | Purpose |
|------|---------|
| `~/.hermes/config.yaml` | Model, compression, memory, vision config |
| `~/.hermes/.env` | Telegram bot token + allowed user ID |
| `~/.hermes/memories/MEMORY.md` | Persistent game knowledge (PKM: entries) |
| `~/.hermes/memories/USER.md` | Matthew's play style preferences |
| `~/.hermes/logs/agent.log` | Session logs |
| `/root/roms/pokemon-blue.gb` | ROM file |
| `/opt/pokemon-agent/` | pokemon-agent venv |
| `/opt/pokemon-agent-src/` | pokemon-agent source (editable install) |

## Key config settings

- **Compression:** enabled at 65% context threshold, keeps last 30 turns — prevents context overflow on long sessions
- **Memory nudge:** every 8 turns — agent reminded to record discoveries with `PKM:` prefix
- **Vision model:** gpt-5.5 with 45s timeout — handles Game Boy screenshot analysis
- **Access:** `TELEGRAM_ALLOWED_USERS` — restricted to Matthew's Telegram ID

## Logs

```bash
journalctl -u hermes -f
journalctl -u pokemon-game -f
tail -f ~/.hermes/logs/agent.log
```

## Restart

```bash
systemctl restart pokemon-game
systemctl restart hermes
```

## Dashboard re-register

```bash
# On CT 102 (claude-ops)
bash /root/homelab/services/ash/deploy.sh
```
