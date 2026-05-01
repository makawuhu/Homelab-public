#!/usr/bin/env bash
# Register ash.yourdomain.com → CT 136 game server dashboard in NPM + Unbound.
# CT 136 must already be running (provisioned manually).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../scripts/lib/deploy-helpers.sh"

NPM_URL="http://192.168.x.31:81"
NPM_CERT_ID=2
OPNSENSE_URL="https://192.168.x.1"

require_secrets /root/.secrets/npm /root/.secrets/opnsense
source /root/.secrets/npm
source /root/.secrets/opnsense

npm_proxy_upsert "$NPM_URL" "ash.yourdomain.com" "192.168.x.172" 9876 "$NPM_CERT_ID"
unbound_dns_upsert "$OPNSENSE_URL" "ash" "yourdomain.com" "192.168.x.31" "Ash Pokemon dashboard"

echo "Done. Dashboard: https://ash.yourdomain.com/dashboard/"
