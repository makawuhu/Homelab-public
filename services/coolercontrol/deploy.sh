#!/usr/bin/env bash
# Deploy CoolerControl on VM 101 (192.168.x.5)
set -euo pipefail

HOST="192.168.x.5"
REMOTE_DIR="/opt/coolercontrol"

echo "Deploying CoolerControl to $HOST..."
ssh "root@$HOST" "mkdir -p $REMOTE_DIR"
scp compose.yml "root@$HOST:$REMOTE_DIR/compose.yml"
ssh "root@$HOST" "cd $REMOTE_DIR && docker compose up -d"
echo "CoolerControl available at http://192.168.x.5:11987"
