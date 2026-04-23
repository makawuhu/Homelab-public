#!/usr/bin/env bash
# Deploy Studio to khris-studio CT
set -euo pipefail

HOST=$(cat .deploy)
REMOTE_DIR="/opt/studio"

echo "Building studio:local on $HOST..."
ssh "root@$HOST" "mkdir -p $REMOTE_DIR"
rsync -a --exclude node_modules --exclude dist . "root@$HOST:$REMOTE_DIR/"
ssh "root@$HOST" "cd $REMOTE_DIR && docker build -t studio:local . && docker compose up -d"
echo "Studio deployed at http://studio.yourdomain.com"
