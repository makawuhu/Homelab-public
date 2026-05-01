# Jellyfin

Media server running on VM 101 (portainer, `192.168.x.5`).

- **Port:** 8096 (HTTP), 8920 (HTTPS)
- **Discovery:** 1900/udp (DLNA), 7359/udp (client discovery)
- **External URL:** https://jellyfin.yourdomain.com
- **Media path:** `/mnt/media` (4 TB WD Red HDD passthrough)
- **GPU:** RTX A2000 12GB — passed through at Proxmox VM level, not in compose. Hardware transcoding must be enabled in Jellyfin settings.
