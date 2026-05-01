#!/usr/bin/env bash
# Deploy Gitea on CT 123 (192.168.x.48)
# Run from claude-ops after provisioning CT 123 and installing Docker CE.
# For initial setup: copy .env.example to .env and fill in GITEA_DB_PASS.
# For migration from CT 119: see README.md for the full dump/restore procedure.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../scripts/lib/deploy-helpers.sh"

HOST="192.168.x.48"
REMOTE_DIR="/opt/gitea"

cd "$SCRIPT_DIR"

if [ ! -f .env ]; then
  echo "ERROR: .env not found. Copy .env.example and fill in values." >&2
  exit 1
fi

preflight_ssh "$HOST"
echo "Deploying Gitea to $HOST..."
ssh "root@$HOST" "mkdir -p $REMOTE_DIR"
scp compose.yml .env "root@$HOST:$REMOTE_DIR/"
ssh "root@$HOST" "cd $REMOTE_DIR && docker compose up -d"

wait_for_http "http://$HOST:3010/api/v1/version" 15 3 "Gitea (http://$HOST:3010)" \
  && echo "Gitea is up at https://gitea.yourdomain.com" \
  || echo "  Check: ssh root@$HOST 'docker logs gitea --tail 30'"
