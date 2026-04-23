#!/usr/bin/env bash
# Deploy Stable Diffusion WebUI on VM 101 (192.168.x.5)
set -euo pipefail

HOST="192.168.x.5"
REMOTE_DIR="/opt/stable-diffusion"

echo "Deploying Stable Diffusion to $HOST..."
ssh "root@$HOST" "mkdir -p $REMOTE_DIR"
scp compose.yml "root@$HOST:$REMOTE_DIR/compose.yml"
ssh "root@$HOST" "cd $REMOTE_DIR && docker compose up -d"
echo "Stable Diffusion available at http://Stable.yourdomain.com"
