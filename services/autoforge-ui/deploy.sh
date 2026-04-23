#!/usr/bin/env bash
# Deploy autoforge-ui to VM 101 (192.168.x.5) via docker compose.
# Creates/updates NPM proxy for autoforge.yourdomain.com.
set -euo pipefail

DOMAIN_FULL="autoforge.yourdomain.com"
HOSTNAME="autoforge"
DOMAIN="yourdomain.com"
FORWARD_HOST="192.168.x.5"
FORWARD_PORT=8055
NPM_URL="http://192.168.x.31:81"
NPM_CERT_ID=2
OPNSENSE_URL="https://192.168.x.1"
REMOTE_HOST="root@192.168.x.5"
REMOTE_PATH="/opt/homelab/services/autoforge-ui"

# ── Secrets ───────────────────────────────────────────────────────────────────
source /root/.secrets/npm
source /root/.secrets/opnsense

# ── Deploy ────────────────────────────────────────────────────────────────────
echo "Deploying autoforge-ui to VM 101..."
ssh "$REMOTE_HOST" "cd $REMOTE_PATH && docker compose up -d --build"

# ── NPM proxy host ────────────────────────────────────────────────────────────
echo ""
echo "Updating NPM proxy host: $DOMAIN_FULL → $FORWARD_HOST:$FORWARD_PORT..."

NPM_TOKEN=$(curl -s -X POST "$NPM_URL/api/tokens" \
  -H "Content-Type: application/json" \
  -d "{\"identity\":\"$NPM_EMAIL\",\"secret\":\"$NPM_PASSWORD\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

EXISTING_PROXY=$(curl -s "$NPM_URL/api/nginx/proxy-hosts" \
  -H "Authorization: Bearer $NPM_TOKEN" \
  | python3 -c "
import sys, json
hosts = json.load(sys.stdin)
match = [h['id'] for h in hosts if '$DOMAIN_FULL' in h.get('domain_names', [])]
print(match[0] if match else '')
")

PROXY_BODY="{
  \"domain_names\": [\"$DOMAIN_FULL\"],
  \"forward_scheme\": \"http\",
  \"forward_host\": \"$FORWARD_HOST\",
  \"forward_port\": $FORWARD_PORT,
  \"ssl_forced\": true,
  \"certificate_id\": $NPM_CERT_ID,
  \"http2_support\": true,
  \"block_exploits\": true,
  \"allow_websocket_upgrade\": true,
  \"enabled\": true
}"

if [ -n "$EXISTING_PROXY" ]; then
  echo "Proxy host exists (ID $EXISTING_PROXY) — updating..."
  curl -s -X PUT "$NPM_URL/api/nginx/proxy-hosts/$EXISTING_PROXY" \
    -H "Authorization: Bearer $NPM_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$PROXY_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print('Updated, forward_host:', d.get('forward_host','?'))"
else
  curl -s -X POST "$NPM_URL/api/nginx/proxy-hosts" \
    -H "Authorization: Bearer $NPM_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$PROXY_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print('Created, ID:', d.get('id','?'))"
fi

# ── Unbound DNS ───────────────────────────────────────────────────────────────
echo ""
echo "Adding Unbound DNS entry: $DOMAIN_FULL → 192.168.x.31..."

EXISTING_DNS=$(curl -sk -u "$OPN_KEY:$OPN_SECRET" "$OPNSENSE_URL/api/unbound/settings/searchHostOverride" \
  | python3 -c "
import sys,json
rows = json.load(sys.stdin).get('rows',[])
match = [r['uuid'] for r in rows if r.get('hostname')=='$HOSTNAME' and r.get('domain')=='$DOMAIN']
print(match[0] if match else '')
")

if [ -n "$EXISTING_DNS" ]; then
  echo "DNS entry already exists (UUID $EXISTING_DNS) — skipping."
else
  curl -sk -u "$OPN_KEY:$OPN_SECRET" -X POST "$OPNSENSE_URL/api/unbound/settings/addHostOverride" \
    -H "Content-Type: application/json" \
    -d "{\"host\":{\"hostname\":\"$HOSTNAME\",\"domain\":\"$DOMAIN\",\"server\":\"192.168.x.31\",\"description\":\"\"}}" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('DNS entry created, UUID:', d.get('uuid','?'))"
  curl -sk -u "$OPN_KEY:$OPN_SECRET" -X POST "$OPNSENSE_URL/api/unbound/service/reconfigure" \
    -H "Content-Type: application/json" -d '{}' > /dev/null
fi

echo ""
echo "Done. AutoForge UI available at https://$DOMAIN_FULL"
