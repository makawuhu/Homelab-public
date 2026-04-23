# CoolerControl

Fan and cooling control daemon on VM 101 (`192.168.x.5`).

- **Port:** 11987 (web UI), 11988 (WebSocket/API — container only, not host-bound)
- **Config:** `/mnt/media/coolercontrol-config`
- Not externally proxied — LAN access only (`http://192.168.x.5:11987`)
