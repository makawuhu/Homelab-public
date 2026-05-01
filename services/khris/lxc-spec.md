# Khris LXC Specification

## Container

| Field | Value |
|-------|-------|
| CT ID | 103 |
| Hostname | khris |
| CPU cores | 8 |
| RAM | 16384 MB (16 GB) |
| Swap | 512 MB |
| Storage | 128 GB (local-zfs) |
| Template | debian-12-standard_12.12-1_amd64.tar.zst |
| Network | bridge=vmbr0, ip=192.168.x.163/24, gw=192.168.x.1 |
| DNS | 192.168.x.1 (OPNsense) |
| Features | nesting=1, keyctl=1 |
| Boot | On boot: yes |

## Software

- Hermes Agent v0.11.0 (NousResearch) — installed via install.sh
- Python 3.11, uv, ripgrep (Hermes dependencies)
- Systemd unit: hermes.service (auto-starts gateway on boot)

## Co-located Services

| Service | Port | Method |
|---------|------|--------|
| Hermes gateway | N/A (polling) | systemd unit |

Note: No inbound ports. Hermes connects outbound to Telegram in polling mode.
