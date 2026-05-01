# Honcho

Persistent AI memory service — stores and surfaces conversation history for AI agents via a [Dialectic API](https://github.com/plastic-labs/honcho).

- **Host:** VM 101 (`192.168.x.5`)
- **Port:** 8050
- **External URL:** https://honcho.yourdomain.com

## Architecture

| Container | Purpose |
|-----------|---------|
| `honcho-api` | FastAPI REST API — Dialectic endpoints for agents to read/write memory |
| `honcho-deriver` | Background worker — derives summaries and context from stored messages |
| `honcho-db` | pgvector (Postgres 15) — stores all messages and embeddings |
| `honcho-redis` | Redis — cache layer |

Source is built locally from `/opt/honcho` (not pulled from a registry). To update, pull the latest source there and redeploy.

## Model config

All LLM work (deriver, summaries, dialectic) uses Claude via Anthropic API. Config is in `config.toml`:

| Role | Model |
|------|-------|
| Deriver | `claude-haiku-4-5-20251001` |
| Summaries | `claude-haiku-4-5-20251001` |
| Dialectic | `claude-haiku-4-5-20251001` |

`LLM_ANTHROPIC_API_KEY` must be set in `.env`.

## Clients

| Client | Workspace | Session |
|--------|-----------|---------|
| nanobot-honcho (chat bot, `@yourhostnamehonchobot`) | `nanobot` | per-user chat session |
| nanobot-stack (GitOps agent, `@yourhostnamebubuilditbot`) | `nanobot` | `nano-gitops-6399984883` |

Each client uses its own session — memory never bleeds between them.

## Deploy

```bash
# From homelab repo root on claude-ops
docker compose -f services/honcho/compose.yml up -d --build
```

The compose file builds the image from `/opt/honcho` on VM 101, so the source must be present there first. Database is provisioned automatically on first start via `scripts/provision_db.py`.

## Data persistence

- Postgres data: Docker volume `honcho-pgdata`
- Redis data: Docker volume `honcho-redis-data`

## Environment variables

| Variable | Description |
|----------|-------------|
| `LLM_ANTHROPIC_API_KEY` | Anthropic API key used by deriver and dialectic |
