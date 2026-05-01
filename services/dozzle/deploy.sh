#!/usr/bin/env bash
# Deploy Dozzle on VM 101 (192.168.x.5)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../scripts/lib/deploy-helpers.sh"

HOST="192.168.x.5"
REMOTE_DIR="/opt/dozzle"

preflight_ssh "$HOST"
remote_compose_deploy "$HOST" "$REMOTE_DIR" "$SCRIPT_DIR/compose.yml"
echo "Dozzle available at http://dozzle.yourdomain.com"
