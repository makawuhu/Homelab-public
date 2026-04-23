# Khris LXC Specification

## Container

| Field | Value |
|-------|-------|
| CT ID | 103 |
| Hostname | khris |
| CPU cores | 4 |
| RAM | 16384 MB (16 GB) |
| Swap | (Proxmox default) |
| Storage | 128 GB (local-zfs) |
| Template | debian-12-standard_12.2-1_amd64.tar.zst |
| Network | bridge=vmbr0, ip=dhcp |
| DNS | 192.168.x.1 (OPNsense) |
| Features | nesting=1, keyctl=1 |
| Boot order | Not on boot (manual start) |

## Software

- OpenClaw (latest)
- Docker CE + Compose v5.1.2 (for webhook-prod, Authentik, Renovate)
- Git (for GitOps repo sync)
- SOPS + age (for secrets decryption)
- Node.js (OpenClaw dependency)

## Proxmox Permissions

KhrisLXCAdmin role on CT 103 (own container). Also has VM.Allocate, VM.Config.CDROM, SDN.Use, Sys.Modify for broader ops work.

## Co-located Services

| Service | Port | Method |
|---------|------|--------|
| OpenClaw gateway | 18789 | Direct (system process, no systemd unit) |
| Authentik (SSO) | 9000/9443 | Docker (server, worker, postgresql, redis) |
| NPM (sandbox) | 80/81/443 | Docker |
| Gitea (sandbox) | 3010/2222 | Docker |
| Uptime Kuma | 3001 | Docker |
| Dozzle | 8888 | Docker |
| FileBrowser | 8080 | Docker |
| Beszel agent | 991 | Docker |
| webhook-prod | 9001 | Docker (currently stopped) |
| Renovate | N/A | Docker (cron job, not always running) |