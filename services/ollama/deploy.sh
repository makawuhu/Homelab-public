#!/usr/bin/env bash
# Deploy Ollama on VM 101 (192.168.x.5) — requires NVIDIA runtime
set -euo pipefail

HOST="192.168.x.5"
REMOTE_DIR="/opt/ollama"

echo "Deploying Ollama to $HOST..."
ssh "root@$HOST" "mkdir -p $REMOTE_DIR"
scp compose.yml "root@$HOST:$REMOTE_DIR/compose.yml"
ssh "root@$HOST" "cd $REMOTE_DIR && docker compose up -d"
echo "Ollama API available at http://ollama.yourdomain.com"
