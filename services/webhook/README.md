# webhook

GitOps deploy webhook for claude-ops (CT 102). Receives push events from Gitea and deploys changed services to their target hosts.

## Architecture

```
Gitea push to main
    ↓
webhook-prod container (port 9000)
    ↓
deploy.sh detects changed services/
    ↓
For each changed service with .deploy file:
  SSH to target host → git pull → docker compose up -d
```

## History

Migrated from CT 102 → CT 103 (khris) on 2026-04-19, then returned to CT 102 (claude-ops) on 2026-04-22 when khris was decommissioned.

## Files

- `compose.yml` — webhook container definition
- `hooks.yaml` — webhook trigger rules
- `scripts/deploy.sh` — main deploy script
- `scripts/entrypoint.sh` — container startup (installs deps)