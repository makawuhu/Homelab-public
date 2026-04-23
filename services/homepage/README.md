# Homepage

Homelab service gateway and dashboard using [Homepage](https://gethomepage.dev).

- **Host:** VM 101 (192.168.x.5)
- **Port:** 3005
- **External URL:** https://homepage.yourdomain.com
- **Image:** ghcr.io/gethomepage/homepage:latest

## Config files

All config lives in `config/` and is SCP'd to `/opt/homepage/config/` on deploy:

| File | Purpose |
|------|---------|
| `services.yaml` | Service groups, links, and API widget integrations |
| `settings.yaml` | Layout, theme, and appearance |
| `widgets.yaml` | Top bar widgets (resources, clock, search, weather) |
| `bookmarks.yaml` | Quick-access admin links |

Homepage hot-reloads config YAML without a container restart.

## API widget integrations

| Service | Widget type | Credential needed |
|---------|-------------|-------------------|
| Jellyfin | `jellyfin` | API key — Jellyfin > Dashboard > Advanced > API Keys |
| Portainer | `portainer` | Static access token — Portainer > User Settings > Access Tokens |
| Uptime Kuma | `uptimekuma` | Status page slug `homelab` must exist |
| Grafana | `grafana` | Admin user/password |

## First-time setup

1. Copy `.env.example` → `.env` and fill in all API keys.
2. In Uptime Kuma, create a Status Page with slug `homelab` containing all monitors.
3. Run: `bash services/homepage/deploy.sh`

## Updating config

Edit any `config/*.yaml` file, commit, and re-run `deploy.sh` to SCP the updated config to the host.
