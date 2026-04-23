# Uptime Kuma

Self-hosted uptime monitoring. See [louislam/uptime-kuma](https://github.com/louislam/uptime-kuma).

- **Host:** VM 101 (`192.168.x.5`)
- **Port:** 3001
- **External URL:** https://status.yourdomain.com

> All monitors use direct IPs and ports — NOT domain names. Using domain names can cause false alerts due to Docker DNS resolving `*.yourdomain.com` to the wrong address inside the portainer VM.

## Setup

1. Start: `docker compose up -d`
2. Access: http://192.168.x.5:3001
3. Configure admin account on first run

## Environment Variables

| Var | Description | Default |
|-----|-------------|---------|
| TZ | Timezone | America/Los_Angeles |

## Data

Data stored in Docker volume `uptime-kuma-data`.
