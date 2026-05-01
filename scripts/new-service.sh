#!/usr/bin/env bash
# new-service.sh — Scaffold a new homelab service and wire up DNS, NPM, and monitoring.
#
# Usage:
#   ./scripts/new-service.sh <name> --port <port> [options]
#
# Options:
#   --port PORT      Host-side port the service listens on (required)
#   --host IP        Target host IP (default: 192.168.x.5)
#   --scheme SCHEME  External URL scheme: http or https (default: https)
#   --no-proxy       Skip DNS + NPM setup (LAN-only / no external URL)
#   --no-monitor     Skip Uptime Kuma monitor
#
# Examples:
#   ./scripts/new-service.sh myapp --port 9000
#   ./scripts/new-service.sh myapp --port 9000 --host 192.168.x.8 --scheme http
#   ./scripts/new-service.sh myapp --port 9000 --no-proxy --no-monitor
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Defaults ──────────────────────────────────────────────────────────────────
SERVICE_NAME=""
HOST="192.168.x.5"
PORT=""
SCHEME="https"
SETUP_PROXY=true
SETUP_MONITOR=true

# ── Arg parsing ───────────────────────────────────────────────────────────────
if [ $# -eq 0 ]; then
  echo "Usage: $0 <name> --port <port> [--host IP] [--scheme http|https] [--no-proxy] [--no-monitor]"
  exit 1
fi

SERVICE_NAME="$1"
shift

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)       PORT="$2";         shift 2 ;;
    --host)       HOST="$2";         shift 2 ;;
    --scheme)     SCHEME="$2";       shift 2 ;;
    --no-proxy)   SETUP_PROXY=false; shift ;;
    --no-monitor) SETUP_MONITOR=false; shift ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

if [ -z "$PORT" ]; then
  echo "ERROR: --port is required"
  exit 1
fi

if [[ ! "$SERVICE_NAME" =~ ^[a-z0-9-]+$ ]]; then
  echo "ERROR: service name must be lowercase alphanumeric with hyphens only"
  exit 1
fi

DOMAIN="${SERVICE_NAME}.yourdomain.com"
EXTERNAL_URL="${SCHEME}://${DOMAIN}"
SERVICE_DIR="${REPO_ROOT}/services/${SERVICE_NAME}"

# Determine host key from IP
case "$HOST" in
  192.168.x.5)   HOST_KEY="portainer-vm" ;;
  192.168.x.8)   HOST_KEY="claude-ops" ;;
  192.168.x.48)  HOST_KEY="gitea" ;;
  192.168.x.47)  HOST_KEY="wazuh" ;;
  192.168.x.167) HOST_KEY="gpu" ;;
  192.168.x.168) HOST_KEY="studio" ;;
  192.168.x.170) HOST_KEY="ai" ;;
  *)              HOST_KEY="" ;;
esac

# Determine if this is a local deploy (CT 102)
LOCAL_HOST="192.168.x.8"
IS_LOCAL=false
if [ "$HOST" = "$LOCAL_HOST" ]; then
  IS_LOCAL=true
fi

# ── Guard: don't overwrite existing service ───────────────────────────────────
if [ -d "$SERVICE_DIR" ]; then
  echo "ERROR: $SERVICE_DIR already exists. Aborting."
  exit 1
fi

# ── Pre-flight: check for conflicting NPM proxy entry ────────────────────────
if [ "$SETUP_PROXY" = true ]; then
  NPM_TOKEN=$(curl -s http://localhost:8002/token/npm \
    -H "X-API-Key: $AUTH_PROXY_API_KEY" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

  CONFLICT_ID=$(curl -s "http://192.168.x.31:81/api/nginx/proxy-hosts" \
    -H "Authorization: Bearer $NPM_TOKEN" \
    | python3 -c "
import sys,json
hosts = json.load(sys.stdin)
match = [h['id'] for h in hosts if '${DOMAIN}' in h.get('domain_names', [])]
print(match[0] if match else '')
")

  if [ -n "$CONFLICT_ID" ]; then
    echo "WARNING: NPM already has a proxy entry for ${DOMAIN} (ID ${CONFLICT_ID})."
    echo "  This will conflict and cause 502 errors."
    read -r -p "Delete the conflicting entry and continue? [y/N] " CONFIRM
    if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
      curl -s -X DELETE "http://192.168.x.31:81/api/nginx/proxy-hosts/${CONFLICT_ID}" \
        -H "Authorization: Bearer $NPM_TOKEN" > /dev/null
      echo "Deleted conflicting NPM entry (ID ${CONFLICT_ID})"
    else
      echo "Aborting. Remove the conflicting entry manually and re-run."
      exit 1
    fi
  fi
fi

echo ""
echo "Creating service: $SERVICE_NAME"
echo "  Host:         $HOST:$PORT"
if [ "$SETUP_PROXY" = true ]; then
  echo "  External URL: $EXTERNAL_URL"
fi
echo "  Proxy setup:  $SETUP_PROXY"
echo "  Monitor:      $SETUP_MONITOR"
echo ""

# ── 1. Generate service directory and files ───────────────────────────────────
mkdir -p "$SERVICE_DIR"

# README.md
cat > "$SERVICE_DIR/README.md" << EOF
# ${SERVICE_NAME}

<!-- TODO: describe what this service does -->

- **Host:** $([ "$IS_LOCAL" = true ] && echo "CT 102 (claude-ops, \`${HOST}\`)" || echo "VM 101 (portainer, \`${HOST}\`)")
- **Port:** ${PORT}
$([ "$SETUP_PROXY" = true ] && echo "- **External URL:** ${EXTERNAL_URL}")
EOF

# compose.yml
cat > "$SERVICE_DIR/compose.yml" << EOF
services:
  ${SERVICE_NAME}:
    image: <image>   # TODO: set image
    container_name: ${SERVICE_NAME}
    ports:
      - "${PORT}:<container_port>"   # TODO: set container port
    restart: unless-stopped
EOF

# .env.example
cat > "$SERVICE_DIR/.env.example" << EOF
# TODO: add required environment variables
EOF

# service.yaml
HEALTHCHECK_LINE=$([ "$SETUP_PROXY" = true ] && echo "healthcheck: ${EXTERNAL_URL}" || echo "healthcheck: null")
cat > "$SERVICE_DIR/service.yaml" << EOF
deployable: true
managed_by: homelab
compose_path: compose.yml
secrets: none
${HEALTHCHECK_LINE}
risk_level: low
data_paths: []
notes: "TODO: describe ${SERVICE_NAME}"
EOF

# .deploy
cat > "$SERVICE_DIR/.deploy" << EOF
HOST=${HOST}
EOF

# deploy.sh
if [ "$IS_LOCAL" = true ]; then
  cat > "$SERVICE_DIR/deploy.sh" << EOF
#!/usr/bin/env bash
# Deploy ${SERVICE_NAME} on CT 102 (claude-ops, ${HOST})
set -euo pipefail

SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
cd "\$SCRIPT_DIR"

echo "Starting ${SERVICE_NAME}..."
docker compose pull --quiet
docker compose up -d --remove-orphans
echo "${SERVICE_NAME} deployed."
EOF
else
  cat > "$SERVICE_DIR/deploy.sh" << EOF
#!/usr/bin/env bash
# Deploy ${SERVICE_NAME} on ${HOST}
set -euo pipefail

REMOTE_REPO="/opt/homelab"
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="\$(cd "\$SCRIPT_DIR/../.." && pwd)"

ssh "root@${HOST}" "
  set -e
  if [ ! -d '\${REMOTE_REPO}' ]; then
    git clone 'http://192.168.x.48:3010/your-gitea-user/homelab.git' '\${REMOTE_REPO}'
  fi
  cd '\${REMOTE_REPO}'
  git fetch origin main
  git reset --hard origin/main
  docker compose -f services/${SERVICE_NAME}/compose.yml pull --quiet
  docker compose -f services/${SERVICE_NAME}/compose.yml up -d --remove-orphans
"
echo "${SERVICE_NAME} deployed to ${HOST}."
EOF
fi

chmod +x "$SERVICE_DIR/deploy.sh"
echo "Scaffolded $SERVICE_DIR"

# ── 2. Add to inventory/services.yaml ────────────────────────────────────────
echo ""
echo "Adding ${SERVICE_NAME} to inventory/services.yaml..."

python3 - "${REPO_ROOT}/inventory/services.yaml" "${SERVICE_NAME}" "${HOST_KEY}" "${SETUP_PROXY}" <<'PYEOF'
import sys, re

path, name, host_key, setup_proxy = sys.argv[1:]

with open(path) as f:
    content = f.read()

# Build the new entry
entry_lines = [f"{name}:"]
if setup_proxy == "true" and host_key:
    entry_lines.append(f"  category: compose_managed")
    entry_lines.append(f"  host: {host_key}")
else:
    entry_lines.append(f"  category: compose_managed")
    if host_key:
        entry_lines.append(f"  host: {host_key}")
entry_lines.append("")  # blank line after entry
new_entry = "\n".join(entry_lines)

# Insert alphabetically — find the first key that sorts after name
lines = content.split("\n")
insert_at = len(lines)
for i, line in enumerate(lines):
    m = re.match(r'^([a-z][a-z0-9-]*):\s*$', line)
    if m and m.group(1) > name:
        insert_at = i
        break

lines.insert(insert_at, new_entry)
with open(path, "w") as f:
    f.write("\n".join(lines))
print(f"Added {name} to inventory/services.yaml")
PYEOF

# ── 3. Update README.md generated sections ───────────────────────────────────
echo ""
echo "Updating README.md generated sections..."
python3 "${REPO_ROOT}/scripts/gen_docs.py" --write

# ── 4. DNS — OPNsense Unbound override ───────────────────────────────────────
if [ "$SETUP_PROXY" = true ]; then
  echo ""
  echo "Adding Unbound DNS override: ${DOMAIN} → 192.168.x.31..."
  OPN_TOKEN=$(curl -s http://localhost:8002/token/opnsense \
    -H "X-API-Key: $AUTH_PROXY_API_KEY" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['key']+':'+d['secret'])")

  ADD_RESULT=$(curl -sk -u "$OPN_TOKEN" \
    -X POST https://192.168.x.1/api/unbound/settings/addHostOverride \
    -H "Content-Type: application/json" \
    -d "{\"host\": {\"hostname\": \"${SERVICE_NAME}\", \"domain\": \"yourdomain.com\", \"server\": \"192.168.x.31\", \"description\": \"${SERVICE_NAME} — added by new-service.sh\"}}")

  if echo "$ADD_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('result')=='saved' else 1)" 2>/dev/null; then
    curl -sk -u "$OPN_TOKEN" \
      -X POST https://192.168.x.1/api/unbound/service/reconfigure \
      -H "Content-Type: application/json" -d '{}' > /dev/null
    echo "DNS: ${DOMAIN} → 192.168.x.31"
  else
    echo "WARNING: DNS add may have failed — check OPNsense Unbound. Response: $ADD_RESULT"
  fi

  # ── 5. NPM proxy host ──────────────────────────────────────────────────────
  echo ""
  echo "Adding NPM proxy host: ${DOMAIN} → ${HOST}:${PORT}..."

  SSL_FORCED=$([ "$SCHEME" = "https" ] && echo "true" || echo "false")

  NPM_RESULT=$(curl -s -X POST "http://192.168.x.31:81/api/nginx/proxy-hosts" \
    -H "Authorization: Bearer $NPM_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"domain_names\": [\"${DOMAIN}\"],
      \"forward_scheme\": \"http\",
      \"forward_host\": \"${HOST}\",
      \"forward_port\": ${PORT},
      \"ssl_forced\": ${SSL_FORCED},
      \"certificate_id\": 2,
      \"http2_support\": true,
      \"block_exploits\": true,
      \"allow_websocket_upgrade\": true,
      \"enabled\": true
    }")

  NPM_ID=$(echo "$NPM_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id','?'))" 2>/dev/null || echo "?")
  if [ "$NPM_ID" != "?" ] && [ "$NPM_ID" != "None" ]; then
    echo "NPM proxy host created (ID $NPM_ID): ${DOMAIN} → ${HOST}:${PORT}"
  else
    echo "WARNING: NPM proxy creation may have failed. Response: $NPM_RESULT"
  fi
fi

# ── 6. Uptime Kuma monitor ────────────────────────────────────────────────────
if [ "$SETUP_MONITOR" = true ]; then
  echo ""
  echo "Adding Uptime Kuma monitor: ${SERVICE_NAME} at ${EXTERNAL_URL}..."
  source /root/.secrets/uptime-kuma

  python3 - <<PYEOF
from uptime_kuma_api import UptimeKumaApi, MonitorType
import sys

api = UptimeKumaApi("${UPTIME_KUMA_URL}")
try:
    api.login("${UPTIME_KUMA_USER}", "${UPTIME_KUMA_PASS}")
    result = api.add_monitor(
        type=MonitorType.HTTP,
        name="${SERVICE_NAME}",
        url="${EXTERNAL_URL}",
        interval=60,
    )
    print(f"Uptime Kuma monitor created (ID {result.get('monitorID', '?')})")
except Exception as e:
    print(f"WARNING: Uptime Kuma monitor creation failed: {e}", file=sys.stderr)
finally:
    api.disconnect()
PYEOF
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "────────────────────────────────────────────────"
echo "Service '${SERVICE_NAME}' scaffolded successfully."
echo ""
echo "Next steps:"
echo "  1. Edit services/${SERVICE_NAME}/compose.yml — set image and container port"
echo "  2. Edit services/${SERVICE_NAME}/.env.example — add required env vars"
echo "  3. Edit services/${SERVICE_NAME}/service.yaml — set notes, risk_level, data_paths"
echo "  4. Commit: git add services/${SERVICE_NAME}/ inventory/services.yaml README.md"
echo "  5. Open a PR — GitOps deploy fires on merge to main"
echo "────────────────────────────────────────────────"
