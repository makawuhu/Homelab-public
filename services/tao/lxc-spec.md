# Tao LXC Specification

## Container

| Field | Value |
|-------|-------|
| CT ID | 133 |
| Hostname | tao |
| CPU cores | 2 |
| RAM | 4096 MB (4 GB) |
| Swap | (Proxmox default) |
| Storage | 32 GB (vmpool) |
| Template | debian-12-standard_12.2-1_amd64.tar.zst |
| Network | bridge=vmbr0, ip=dhcp |
| DNS | 192.168.x.1 (OPNsense) |
| Features | nesting=1, keyctl=1 |
| Boot | On boot: yes |

## Software

- OpenClaw 2026.4.15
- Docker CE 29.4.0 (installed, no active containers)
- Git (for cloning homelab repo)

## Proxmox Permissions

Created under KhrisLXCAdmin role. No special permissions beyond standard CT management.

## Co-located Services

| Service | Port | Method |
|---------|------|--------|
| OpenClaw gateway | 18789 | Direct (system process) |

Note: Tao has Docker installed but runs only OpenClaw directly. No active Docker containers.