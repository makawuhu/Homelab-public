#!/usr/bin/env bash
# Deploy Beszel hub + agents across all Docker hosts
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HUB_HOST="192.168.x.5"
HUB_DIR="/opt/beszel"

# Docker hosts that need an agent
AGENT_HOSTS=(
  "192.168.x.8"   # CT 102 — claude-ops
  "192.168.x.48"  # CT 123 — gitea
  "192.168.x.51"  # CT 125 — ollama
)

AGENT_DIR="/opt/beszel-agent"

echo "=== Deploying Beszel hub to $HUB_HOST ==="
ssh "root@$HUB_HOST" "mkdir -p $HUB_DIR"
scp "$SCRIPT_DIR/compose.yml" "root@$HUB_HOST:$HUB_DIR/compose.yml"
ssh "root@$HUB_HOST" "cd $HUB_DIR && docker compose pull && docker compose up -d"
echo "Hub deployed → https://beszel.yourdomain.com"

echo ""
echo "=== Deploying Beszel agent to remaining hosts ==="
for HOST in "${AGENT_HOSTS[@]}"; do
  echo "--- $HOST ---"
  if [[ "$HOST" == "192.168.x.8" ]]; then
    # CT 102 is this machine — deploy locally
    mkdir -p "$AGENT_DIR"
    cp "$SCRIPT_DIR/agent/compose.yml" "$AGENT_DIR/compose.yml"
    cd "$AGENT_DIR" && docker compose pull && docker compose up -d
  else
    ssh "root@$HOST" "mkdir -p $AGENT_DIR"
    scp "$SCRIPT_DIR/agent/compose.yml" "root@$HOST:$AGENT_DIR/compose.yml"
    ssh "root@$HOST" "cd $AGENT_DIR && docker compose pull && docker compose up -d"
  fi
  echo "Agent running on $HOST:991"
done

echo ""
echo "Done. Add any new hosts in the Beszel UI at https://beszel.yourdomain.com"
echo "Agent address format: <ip>:991"
