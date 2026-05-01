# Portainer

**Host:** VM 101 (portainer) · `192.168.x.5`
**GPU:** NVIDIA RTX A2000 12GB (passthrough, PCI 0000:65:00)
**Storage:** 128G OS (ZFS) + 4TB HDD passthrough (WD WD40EFPX)

## Access

| URL | Description |
|-----|-------------|
| `https://portainer.yourdomain.com` | External (via NPM) |
| `https://192.168.x.5:9443` | Direct LAN HTTPS |

## Notes

- QEMU guest agent may not be running — access via console if SSH fails
- GPU passthrough is configured at the Proxmox level, not in compose
- Port 8000 (Edge Agent) and 9000 (HTTP) are exposed on the container network only — not bound to the host interface
