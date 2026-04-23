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
HOST="192.168.x.45"
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

DOMAIN="${SERVICE_NAME}-dev.yourdomain.com"
EXTERNAL_URL="${SCHEME}://${DOMAIN}"
SERVICE_DIR="${REPO_ROOT}/services/${SERVICE_NAME}"
REMOTE_DIR="/opt/${SERVICE_NAME}"

# Determine if this is a local deploy (CT 102) or remote
LOCAL_HOST="192.168.x.45"
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
  source /root/.secrets/npm
  NPM_TOKEN=$(curl -s -X POST "${NPM_URL}/api/tokens" \
    -H "Content-Type: application/json" \
    -d "{\"identity\":\"${NPM_EMAIL}\",\"secret\":\"${NPM_PASSWORD}\"}" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

  CONFLICT_ID=$(curl -s "${NPM_URL}/api/nginx/proxy-hosts" \
    -H "Authorization: Bearer $NPM_TOKEN" \
    | python3 -c "
import sys,json
hosts = json.load(sys.stdin)
match = [h['id'] for h in hosts if '${DOMAIN}' in h.get('domain_names', [])]
print(match[0] if match else '')
")

  if [ -n "$CONFLICT_ID" ]; then
    echo "⚠ WARNING: NPM already has a proxy entry for ${DOMAIN} (ID ${CONFLICT_ID})."
    echo "  This will conflict and cause 502 errors."
    read -r -p "Delete the conflicting entry automatically and continue? [y/N] " CONFIRM
    if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
      curl -s -X DELETE "${NPM_URL}/api/nginx/proxy-hosts/${CONFLICT_ID}" \
        -H "Authorization: Bearer $NPM_TOKEN" > /dev/null
      echo "✓ Deleted conflicting NPM entry (ID ${CONFLICT_ID})"
    else
      echo "Aborting. Remove the conflicting entry manually and re-run."
      exit 1
    fi
  fi

  # Sandbox NPM runs as a Docker container — no stale conf check needed.
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

# deploy.sh
if [ "$IS_LOCAL" = true ]; then
  cat > "$SERVICE_DIR/deploy.sh" << EOF
#!/usr/bin/env bash
# Deploy ${SERVICE_NAME} on CT 102 (claude-ops, ${HOST})
set -euo pipefail

SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
cd "\$SCRIPT_DIR"

echo "Building and starting ${SERVICE_NAME}..."
docker compose up -d --build

echo "Waiting for ${SERVICE_NAME} to become ready..."
for i in \$(seq 1 12); do
  if curl -sf http://${HOST}:${PORT} > /dev/null 2>&1; then
    echo "✓ ${SERVICE_NAME} is up at ${EXTERNAL_URL}"
    exit 0
  fi
  sleep 5
done
echo "⚠ ${SERVICE_NAME} did not respond on port ${PORT} after 60s — check 'docker logs ${SERVICE_NAME}'"
EOF
else
  cat > "$SERVICE_DIR/deploy.sh" << EOF
#!/usr/bin/env bash
# Deploy ${SERVICE_NAME} on ${HOST}
set -euo pipefail

HOST="${HOST}"
REMOTE_DIR="${REMOTE_DIR}"

SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
cd "\$SCRIPT_DIR"

if [ ! -f .env ]; then
  echo "ERROR: .env not found. Copy .env.example and fill in values."
  exit 1
fi

echo "Deploying ${SERVICE_NAME} to \$HOST..."
ssh "root@\$HOST" "mkdir -p \$REMOTE_DIR"
scp compose.yml .env "root@\$HOST:\$REMOTE_DIR/"
ssh "root@\$HOST" "cd \$REMOTE_DIR && docker compose up -d"

echo "Waiting for ${SERVICE_NAME} to become ready..."
for i in \$(seq 1 12); do
  if curl -sf http://${HOST}:${PORT} > /dev/null 2>&1; then
    echo "✓ ${SERVICE_NAME} is up at ${EXTERNAL_URL}"
    exit 0
  fi
  sleep 5
done
echo "⚠ ${SERVICE_NAME} did not respond on port ${PORT} after 60s — check 'docker logs ${SERVICE_NAME}' on \$HOST"
EOF
fi

chmod +x "$SERVICE_DIR/deploy.sh"
echo "✓ Scaffolded $SERVICE_DIR"

# ── 2. DNS — OPNsense Unbound override ────────────────────────────────────────
if [ "$SETUP_PROXY" = true ]; then
  echo ""
  echo "Adding Unbound DNS override: ${DOMAIN} → 192.168.x.31..."
  source /root/.secrets/opnsense

  ADD_RESULT=$(curl -sk -u "$OPN_KEY:$OPN_SECRET" \
    -X POST https://192.168.x.1/api/unbound/settings/addHostOverride \
    -H "Content-Type: application/json" \
    -d "{\"host\": {\"hostname\": \"${SERVICE_NAME}-dev\", \"domain\": \"yourdomain.com\", \"server\": \"192.168.x.45\", \"description\": \"${SERVICE_NAME}-dev sandbox — added by new-service.sh\"}}")

  if echo "$ADD_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('result')=='saved' else 1)" 2>/dev/null; then
    curl -sk -u "$OPN_KEY:$OPN_SECRET" \
      -X POST https://192.168.x.1/api/unbound/service/reconfigure \
      -H "Content-Type: application/json" -d '{}' > /dev/null
    echo "✓ DNS: ${DOMAIN} → 192.168.x.45"
  else
    echo "⚠ DNS add may have failed — check OPNsense Unbound. Response: $ADD_RESULT"
  fi

  # ── 3. NPM proxy host ──────────────────────────────────────────────────────
  echo ""
  echo "Adding NPM proxy host: ${DOMAIN} → ${HOST}:${PORT}..."

  SSL_FORCED=$([ "$SCHEME" = "https" ] && echo "true" || echo "false")

  NPM_RESULT=$(curl -s -X POST "${NPM_URL}/api/nginx/proxy-hosts" \
    -H "Authorization: Bearer $NPM_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"domain_names\": [\"${DOMAIN}\"],
      \"forward_scheme\": \"http\",
      \"forward_host\": \"${HOST}\",
      \"forward_port\": ${PORT},
      \"ssl_forced\": ${SSL_FORCED},
      \"certificate_id\": 3,
      \"http2_support\": true,
      \"block_exploits\": true,
      \"allow_websocket_upgrade\": true,
      \"enabled\": true
    }")

  NPM_ID=$(echo "$NPM_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id','?'))" 2>/dev/null || echo "?")
  if [ "$NPM_ID" != "?" ] && [ "$NPM_ID" != "None" ]; then
    echo "✓ NPM proxy host created (ID $NPM_ID): ${DOMAIN} → ${HOST}:${PORT}"
  else
    echo "⚠ NPM proxy creation may have failed. Response: $NPM_RESULT"
  fi
fi

# ── 4. Uptime Kuma monitor ────────────────────────────────────────────────────
if [ "$SETUP_MONITOR" = true ]; then
  echo ""
  echo "Adding Uptime Kuma monitor: ${SERVICE_NAME} at http://${HOST}:${PORT}..."
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
        url="http://${HOST}:${PORT}",
        interval=60,
    )
    print(f"✓ Uptime Kuma monitor created (ID {result.get('monitorID', '?')})")
except Exception as e:
    print(f"⚠ Uptime Kuma monitor creation failed: {e}", file=sys.stderr)
finally:
    api.disconnect()
PYEOF
fi

# ── 5. Update CLAUDE.md ───────────────────────────────────────────────────────
echo ""
echo "Updating CLAUDE.md..."

HOST_LABEL=$([ "$IS_LOCAL" = true ] && echo "CT 102" || echo "VM 101")

python3 - "${REPO_ROOT}/CLAUDE.md" "${SERVICE_NAME}" "${PORT}" "${HOST_LABEL}" "${SETUP_PROXY}" "${EXTERNAL_URL}" "${HOST}" <<'PYEOF'
import sys

path, name, port, host_label, setup_proxy, external_url, host = sys.argv[1:]

with open(path) as f:
    content = f.read()

# Insert into repo structure — after homelab-assistant line
service_line = f"  {name}/".ljust(22) + f"<!-- TODO: describe --> — {host_label} :{port}"
content = content.replace(
    "  homelab-assistant/ AI homelab management chat UI — CT 102 :8001",
    "  homelab-assistant/ AI homelab management chat UI — CT 102 :8001\n" + service_line
)

# Insert into URL table — before the nginx line (always last)
if setup_proxy == "true":
    url_line = f"| {external_url} | {host}:{port} |"
    content = content.replace(
        "| http://nginx.yourdomain.com | 192.168.x.31:81 |",
        url_line + "\n| http://nginx.yourdomain.com | 192.168.x.31:81 |"
    )

with open(path, "w") as f:
    f.write(content)

print("✓ CLAUDE.md updated")
PYEOF

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "────────────────────────────────────────────────"
echo "Service '${SERVICE_NAME}' scaffolded successfully."
echo ""
echo "Next steps:"
echo "  1. Edit services/${SERVICE_NAME}/compose.yml — set image and container port"
echo "  2. Edit services/${SERVICE_NAME}/.env.example — add required env vars"
echo "  3. Copy .env.example → .env on the target host and fill in values"
echo "  4. Run: bash services/${SERVICE_NAME}/deploy.sh"
echo "  5. Update services/${SERVICE_NAME}/README.md with service description"
echo "  6. Commit: git add services/${SERVICE_NAME}/ CLAUDE.md && git commit"
echo "────────────────────────────────────────────────"
