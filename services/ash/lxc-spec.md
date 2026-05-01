# Ash LXC Specification

## Container

| Field | Value |
|-------|-------|
| CT ID | 136 |
| Hostname | ash |
| CPU cores | 4 |
| RAM | 8192 MB (8 GB) |
| Swap | 512 MB |
| Storage | 32 GB (vmpool) |
| Template | debian-12-standard_12.12-1_amd64.tar.zst |
| Network | bridge=vmbr0, ip=192.168.x.172/24, gw=192.168.x.1 |
| DNS | 192.168.x.1 (OPNsense) |
| Features | nesting=1, keyctl=1 |
| Boot | On boot: yes |

## Software

- Hermes Agent v0.11.0 (NousResearch) — installed via install.sh
- Python 3.11, uv, ripgrep (Hermes dependencies)
- pokemon-agent (NousResearch/pokemon-agent) + PyBoy — venv at /opt/pokemon-agent
- Systemd units: hermes.service, pokemon-game.service

## Co-located Services

| Service | Port | Method |
|---------|------|--------|
| Hermes gateway | N/A (Telegram polling) | systemd unit |
| pokemon-agent game server | 9876 | systemd unit |
