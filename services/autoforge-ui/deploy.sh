#!/usr/bin/env bash
# Deploy autoforge-ui to VM 101 (192.168.x.5) via docker compose.
# Creates/updates NPM proxy and Unbound DNS for autoforge.yourdomain.com.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../scripts/lib/deploy-helpers.sh"

HOST="192.168.x.5"
NPM_URL="http://192.168.x.31:81"
NPM_CERT_ID=2
OPNSENSE_URL="https://192.168.x.1"

require_secrets /root/.secrets/npm /root/.secrets/opnsense
source /root/.secrets/npm
source /root/.secrets/opnsense

preflight_ssh "$HOST"
echo "Deploying autoforge-ui to VM 101..."
ssh "root@$HOST" "cd /opt/homelab/services/autoforge-ui && docker compose up -d --build"

npm_proxy_upsert "$NPM_URL" "autoforge.yourdomain.com" "$HOST" 8055 "$NPM_CERT_ID"
unbound_dns_upsert "$OPNSENSE_URL" "autoforge" "yourdomain.com" "192.168.x.31" "AutoForge UI"

echo "Done. AutoForge UI available at https://autoforge.yourdomain.com"
