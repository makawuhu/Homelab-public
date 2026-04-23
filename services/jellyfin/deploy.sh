#!/usr/bin/env bash
# Deploy Jellyfin on VM 101 (192.168.x.5)
set -euo pipefail

HOST="192.168.x.5"
REMOTE_DIR="/opt/jellyfin"

echo "Deploying Jellyfin to $HOST..."
ssh "root@$HOST" "mkdir -p $REMOTE_DIR"
scp compose.yml "root@$HOST:$REMOTE_DIR/compose.yml"
ssh "root@$HOST" "cd $REMOTE_DIR && docker compose up -d"
echo "Jellyfin available at https://jellyfin.yourdomain.com"
