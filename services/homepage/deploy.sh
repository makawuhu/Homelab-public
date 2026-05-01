#!/usr/bin/env bash
# Deploy Homepage dashboard on VM 101 (192.168.x.5).
# Seeds .env, brings up compose via remote homelab checkout, sets up NPM + DNS.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../scripts/lib/deploy-helpers.sh"

HOST="192.168.x.5"
REMOTE_DIR="/opt/homelab/services/homepage"
NPM_URL="http://192.168.x.31:81"
NPM_CERT_ID=2
OPNSENSE_URL="https://192.168.x.1"

if [ ! -f "$SCRIPT_DIR/.env" ]; then
  echo "ERROR: .env not found. Copy .env.example and fill in values." >&2
  exit 1
fi

require_secrets /root/.secrets/npm /root/.secrets/opnsense
source /root/.secrets/npm
source /root/.secrets/opnsense

preflight_ssh "$HOST"
echo "Deploying Homepage to $HOST..."
ssh "root@$HOST" "mkdir -p $REMOTE_DIR"
scp "$SCRIPT_DIR/.env" "root@$HOST:$REMOTE_DIR/.env"
ssh "root@$HOST" "cd /opt/homelab && docker compose -f services/homepage/compose.yml pull --quiet && docker compose -f services/homepage/compose.yml up -d"

npm_proxy_upsert "$NPM_URL" "homepage.yourdomain.com" "192.168.x.31" 3005 "$NPM_CERT_ID"
unbound_dns_upsert "$OPNSENSE_URL" "homepage" "yourdomain.com" "192.168.x.31" "Homepage dashboard"

echo "Done. Homepage available at https://homepage.yourdomain.com"
