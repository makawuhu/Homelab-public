# Wazuh

Security monitoring platform (SIEM/XDR) on CT 122 (`wazuh`, `192.168.x.47`).

- **Port:** 8443 (dashboard)
- **External URL:** https://wazuh.yourdomain.com
- **Login:** `admin` / `INDEXER_PASSWORD`

## Services

| Container | Purpose |
|-----------|---------|
| `wazuh-manager` | Security event collection, analysis, and alerting |
| `wazuh-indexer` | OpenSearch — stores and indexes security events |
| `wazuh-dashboard` | Web UI for viewing alerts and managing agents |

## Agent ports (direct — not through NPM)

| Port | Purpose |
|------|---------|
| `1514` | Agent event ingestion |
| `1515` | Agent enrollment/registration |
| `514/udp` | Syslog ingestion |
| `55000` | Manager REST API |

## Deploy

```bash
cp .env.example .env
# Set strong passwords for all three variables
./deploy.sh
```

`deploy.sh` handles:
1. `vm.max_map_count=262144` on the Docker host (OpenSearch requirement)
2. TLS certificate generation (first-time only, via official Wazuh helper)
3. Config file setup from official wazuh-docker repo
4. `docker compose up -d` + health check (allow 2–3 min to start)

## Environment variables

| Variable | Description |
|---|---|
| `INDEXER_PASSWORD` | OpenSearch admin password — also the dashboard login |
| `API_PASSWORD` | Wazuh manager API password (user: `wazuh-wui`) |
| `DASHBOARD_PASSWORD` | Internal kibanaserver account password |

## Password setup (critical)

**`internal_users.yml` must have pre-hashed passwords matching `.env` BEFORE first startup.** The Wazuh docker images do NOT auto-hash env vars into OpenSearch's user database — the hash in `internal_users.yml` and the env var must be in sync from the start.

To generate a bcrypt hash for a new password:
```bash
docker run --rm -e JAVA_HOME=/usr/share/wazuh-indexer/jdk \
  --entrypoint bash wazuh/wazuh-indexer:4.9.2 \
  /usr/share/wazuh-indexer/plugins/opensearch-security/tools/hash.sh -p "YourPassword"
```

Update `admin` and `kibanaserver` hashes in `/opt/wazuh/config/wazuh_indexer/internal_users.yml` on the host **in-place** (use Python `open(f,"w").write(...)`, NOT `sed -i` — sed replaces the inode and Docker bind-mounts stop seeing the new file).

`INDEXER_PASSWORD` = admin user password = `kibanaserver` user password = `DASHBOARD_PASSWORD`.

`API_PASSWORD` must meet Wazuh complexity: uppercase + lowercase + digit + special char (`_` counts).

## Notes

- Dashboard runs HTTPS internally — NPM proxies to it with `forward_scheme: https`
- Certificates are generated once and stored in `/opt/wazuh/config/wazuh_indexer_ssl_certs/`
- Cert dir permissions must be `755`, cert files must be `644` (container runs as non-root)
- Agent installation: https://documentation.wazuh.com/current/installation-guide/wazuh-agent/
