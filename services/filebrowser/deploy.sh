#!/usr/bin/env bash
# Deploy filebrowser on VM 101 (192.168.x.5)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../scripts/lib/deploy-helpers.sh"

cd "$SCRIPT_DIR"
echo "Building and starting filebrowser..."
docker compose up -d --build

wait_for_http "http://192.168.x.5:8085" 12 5 "filebrowser (http://192.168.x.5:8085)" \
  && echo "✓ filebrowser is up at https://filebrowser-dev.yourdomain.com" \
  || echo "  Check: docker logs filebrowser"
