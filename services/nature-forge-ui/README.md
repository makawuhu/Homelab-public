# nature-forge-ui

Nature-Forge GPU integration UI. Allows submitting print jobs to the GPU pipeline from a web interface.

- **Host:** VM 101 (`192.168.x.5`)
- **Port:** 8056
- **External URL:** https://nature-forge.yourdomain.com
- **Managed by:** homelab (docker compose, GitOps webhook for config; manual rebuild for code changes)

## Deploy

This service uses a local `Dockerfile` (`build: .`) with no registry image. The GitOps webhook deploys compose config changes automatically, but **does not rebuild the image**. The remote webhook path runs `docker compose pull` + `docker compose up -d`, which skips local builds.

**For compose-only changes** (env vars, ports, volumes): merge to `main` — webhook handles it.

**For code or Dockerfile changes**: rebuild manually on VM 101 first:
```bash
ssh root@192.168.x.5 "cd /opt/homelab/services/nature-forge-ui && docker compose build && docker compose up -d"
```

## Notes

- Dockerfile-based build (no registry image)
- GPU backend is on VM 131 (`192.168.x.167`)
