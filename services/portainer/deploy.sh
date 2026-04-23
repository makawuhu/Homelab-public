#!/usr/bin/env bash
# Deploy Portainer on VM 101 (192.168.x.5)
set -euo pipefail

HOST="192.168.x.5"
REMOTE_DIR="/opt/portainer"

echo "Deploying Portainer to $HOST..."
ssh "root@$HOST" "mkdir -p $REMOTE_DIR"
scp compose.yml "root@$HOST:$REMOTE_DIR/compose.yml"
ssh "root@$HOST" "cd $REMOTE_DIR && docker compose up -d"
echo "Portainer available at https://$HOST:9443"
