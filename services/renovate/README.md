# Renovate

Automated dependency update bot for Gitea repos. See [renovatebot/renovate](https://github.com/renovatebot/renovate) for full documentation.

**This is a one-shot job — not a persistent service.** Run it manually or via cron; it exits after scanning repos.

- **Platform:** Gitea at `http://192.168.x.48:3010`
- **Bot user:** `renovate-bot` (Gitea account)
- **Host:** CT 102 (192.168.x.8) — returned from CT 103 on 2026-04-22

## Run

```bash
# One-shot run
bash services/renovate/run.sh

# Or directly
docker compose -f services/renovate/compose.yml run --rm renovate
```

## Config

`renovate.json` — defines which repos to scan and update rules. The `RENOVATE_CONFIG_FILE` env var points the container at this file (required — Renovate ignores it otherwise).

## Environment variables

Set in `.env` (see `.env.example`):

| Variable | Description |
|----------|-------------|
| `RENOVATE_TOKEN` | Gitea personal access token for `renovate-bot` user |

## Notes

- Renovate cache is stored in a Docker volume (`renovate-cache`) at `/tmp/renovate/cache` — cache uid must be `1000`
- `RENOVATE_ONBOARDING=false` — skips onboarding PRs on repos without a `renovate.json`
- PRs opened by Renovate go through the normal GitOps merge → deploy pipeline
- Requires `apparmor=unconfined` (LXC Docker constraint)