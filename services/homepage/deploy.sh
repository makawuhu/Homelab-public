#!/usr/bin/env bash
# Deploy Homepage dashboard on VM 101 (192.168.x.5).
set -euo pipefail

HOST="192.168.x.5"
REMOTE_DIR="/opt/homelab/services/homepage"
DOMAIN_FULL="homepage.yourdomain.com"
FORWARD_PORT=3005
NPM_CERT_ID=2
NPM_URL="http://192.168.x.31:81"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f .env ]; then
  echo "ERROR: .env not found. Copy .env.example and fill in values."
  exit 1
fi

# ── Deploy ────────────────────────────────────────────────────────────────────
echo "Deploying Homepage to $HOST..."
# Seed .env on the remote repo checkout — tracked files are handled by GitOps
ssh "root@$HOST" "mkdir -p $REMOTE_DIR"
scp .env "root@$HOST:$REMOTE_DIR/.env"
ssh "root@$HOST" "cd /opt/homelab && docker compose -f services/homepage/compose.yml pull && docker compose -f services/homepage/compose.yml up -d"

# ── DNS override ──────────────────────────────────────────────────────────────
echo ""
echo "Adding Unbound DNS override: $DOMAIN_FULL → 192.168.x.31..."
source /root/.secrets/opnsense
curl -sk -u "$OPN_KEY:$OPN_SECRET" \
  -X POST https://192.168.x.1/api/unbound/settings/addHostOverride \
  -H "Content-Type: application/json" \
  -d '{"host":{"hostname":"homepage","domain":"yourdomain.com","server":"192.168.x.31","description":"Homepage dashboard"}}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('DNS:', d.get('result','?'))"
curl -sk -u "$OPN_KEY:$OPN_SECRET" \
  -X POST https://192.168.x.1/api/unbound/service/reconfigure \
  -H "Content-Type: application/json" -d '{}'
echo "DNS applied."

# ── NPM proxy host ────────────────────────────────────────────────────────────
echo ""
echo "Creating NPM proxy host: $DOMAIN_FULL → $HOST:$FORWARD_PORT..."
source /root/.secrets/npm
NPM_TOKEN=$(curl -s -X POST "$NPM_URL/api/tokens" \
  -H "Content-Type: application/json" \
  -d "{\"identity\":\"$NPM_EMAIL\",\"secret\":\"$NPM_PASSWORD\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

EXISTING=$(curl -s "$NPM_URL/api/nginx/proxy-hosts" \
  -H "Authorization: Bearer $NPM_TOKEN" \
  | python3 -c "
import sys, json
hosts = json.load(sys.stdin)
match = [h['id'] for h in hosts if '$DOMAIN_FULL' in h.get('domain_names', [])]
print(match[0] if match else '')
")

if [ -n "$EXISTING" ]; then
  echo "NPM proxy already exists (ID $EXISTING) — skipping creation."
else
  curl -s -X POST "$NPM_URL/api/nginx/proxy-hosts" \
    -H "Authorization: Bearer $NPM_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"domain_names\":[\"$DOMAIN_FULL\"],
      \"forward_scheme\":\"http\",
      \"forward_host\":\"$HOST\",
      \"forward_port\":$FORWARD_PORT,
      \"ssl_forced\":true,
      \"certificate_id\":$NPM_CERT_ID,
      \"http2_support\":true,
      \"block_exploits\":true,
      \"allow_websocket_upgrade\":true,
      \"enabled\":true
    }" | python3 -c "import sys,json; d=json.load(sys.stdin); print('NPM proxy created, ID:', d.get('id','?'))"
fi

echo ""
echo "Done. Homepage available at https://$DOMAIN_FULL"
