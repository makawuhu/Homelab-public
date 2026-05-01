# Anri LXC Specification

## Container

| Field | Value |
|-------|-------|
| CT ID | 129 |
| Hostname | anri |
| CPU cores | 8 |
| RAM | 16384 MB (16 GB) |
| Swap | (Proxmox default) |
| Storage | 128 GB (local-zfs) |
| Template | debian-12-standard_12.2-1_amd64.tar.zst |
| Network | bridge=vmbr0, ip=192.168.x.165/24, gw=192.168.x.1 |
| DNS | 192.168.x.1 (OPNsense) |
| Features | nesting=1, keyctl=1 |
| Boot | On boot: yes |

## Software

- OpenClaw 2026.4.10
- Docker CE 29.4.0 (installed, no active containers)
- Git (for repo access)
- SOPS + age (for secrets decryption, if needed)

## Proxmox Permissions

Created under KhrisLXCAdmin role. No special permissions beyond standard CT management.

## Co-located Services

| Service | Port | Method |
|---------|------|--------|
| OpenClaw gateway | 18789 | Direct (system process) |

Note: Anri has Docker installed but runs only OpenClaw directly. No active Docker containers.