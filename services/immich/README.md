# Immich

Self-hosted photo and video backup. See [immich-app/immich](https://github.com/immich-app/immich) for full documentation.

- **Host:** VM 101 (`192.168.x.5`)
- **Port:** 2283
- **External URL:** https://immich.yourdomain.com

## Stack

| Container | Purpose |
|-----------|---------|
| `immich` | Main server + web UI |
| `immich-ml` | Machine learning (face recognition, CLIP search) |
| `immich-db` | pgvecto-rs (Postgres + vector extension) |
| `immich-redis` | Cache |

## Environment variables

| Variable | Description |
|----------|-------------|
| `DB_USERNAME` | Postgres username |
| `DB_PASSWORD` | Postgres password |
| `DB_DATABASE_NAME` | Postgres database name |
