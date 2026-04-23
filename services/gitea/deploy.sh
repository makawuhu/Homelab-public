#!/usr/bin/env bash
# Deploy Gitea on CT 123 (192.168.x.48)
# Run from claude-ops after provisioning CT 123 and installing Docker CE.
# For initial setup: copy .env.example to .env and fill in GITEA_DB_PASS.
# For migration from CT 119: see README.md for the full dump/restore procedure.
set -euo pipefail

HOST="192.168.x.48"
REMOTE_DIR="/opt/gitea"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f .env ]; then
  echo "ERROR: .env not found. Copy .env.example and fill in values."
  exit 1
fi

echo "Deploying Gitea to $HOST..."
ssh "root@$HOST" "mkdir -p $REMOTE_DIR"
scp compose.yml .env "root@$HOST:$REMOTE_DIR/"
ssh "root@$HOST" "cd $REMOTE_DIR && docker compose up -d"

echo "Waiting for Gitea to become ready..."
for i in $(seq 1 15); do
  if curl -sf "http://$HOST:3010/api/v1/version" > /dev/null 2>&1; then
    echo "Gitea is up at https://gitea.yourdomain.com"
    exit 0
  fi
  echo "  Attempt $i/15 — waiting..."
  sleep 3
done
echo "WARNING: Gitea did not respond on port 3010 after 45 seconds"
echo "  Check: ssh root@$HOST 'docker logs gitea --tail 30'"
