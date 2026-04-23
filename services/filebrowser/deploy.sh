#!/usr/bin/env bash
# Deploy filebrowser on CT 102 (claude-ops, 192.168.x.45)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Building and starting filebrowser..."
docker compose up -d --build

echo "Waiting for filebrowser to become ready..."
for i in $(seq 1 12); do
  if curl -sf http://192.168.x.45:8085 > /dev/null 2>&1; then
    echo "✓ filebrowser is up at https://filebrowser-dev.yourdomain.com"
    exit 0
  fi
  sleep 5
done
echo "⚠ filebrowser did not respond on port 8085 after 60s — check 'docker logs filebrowser'"
