#!/usr/bin/env bash
# Deploy / verify a curated subset of services that support idempotent redeployment.
# VM 101 Docker services are deployed directly on the portainer VM (not from here).
# monitoring is a Portainer git-backed stack — redeploy via Portainer UI/API.
# homelab-assistant is deployed on this LXC — run services/homelab-assistant/deploy.sh directly.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

services=(
  "$REPO_ROOT/network/nginxproxymanager/deploy.sh"
  "$REPO_ROOT/services/portainer/deploy.sh"
)

for script in "${services[@]}"; do
  echo "=== $(basename "$(dirname "$script")") ==="
  bash "$script"
  echo ""
done
