#!/usr/bin/env bash
# Deploy Wazuh (manager + indexer + dashboard) on CT 122 (192.168.x.47)
set -euo pipefail

HOST="192.168.x.47"
REMOTE_DIR="/opt/wazuh"
WAZUH_VERSION="4.9.2"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f .env ]; then
  echo "ERROR: .env not found. Copy .env.example and fill in values."
  exit 1
fi

# ── 1. Set vm.max_map_count (required by OpenSearch/indexer) ──────────────────
echo "Setting vm.max_map_count on $HOST..."
ssh "root@$HOST" "sysctl -w vm.max_map_count=262144 && \
  grep -q 'vm.max_map_count' /etc/sysctl.conf && \
  sed -i 's/.*vm.max_map_count.*/vm.max_map_count=262144/' /etc/sysctl.conf || \
  echo 'vm.max_map_count=262144' >> /etc/sysctl.conf"
echo "✓ vm.max_map_count=262144"

# ── 2. Generate TLS certificates (first-time only) ───────────────────────────
echo ""
echo "Checking certificates..."
CERTS_EXIST=$(ssh "root@$HOST" "[ -d $REMOTE_DIR/config/wazuh_indexer_ssl_certs ] && echo yes || echo no")

if [ "$CERTS_EXIST" = "no" ]; then
  echo "Generating Wazuh TLS certificates via official helper..."
  ssh "root@$HOST" "
    cd /tmp && rm -rf wazuh-docker-certs && \
    git clone --quiet --depth 1 --branch v${WAZUH_VERSION} https://github.com/wazuh/wazuh-docker.git wazuh-docker-certs && \
    cd wazuh-docker-certs/single-node && \
    docker compose -f generate-indexer-certs.yml run --rm generator && \
    mkdir -p $REMOTE_DIR/config && \
    cp -r config/wazuh_indexer_ssl_certs $REMOTE_DIR/config/ && \
    cd /tmp && rm -rf wazuh-docker-certs"
  echo "✓ Certificates generated"
else
  echo "✓ Certificates already exist — skipping"
fi

# ── 3. Pull config files from official wazuh-docker repo ─────────────────────
echo ""
echo "Pulling Wazuh config files..."
ssh "root@$HOST" "cd $REMOTE_DIR && \
  [ -d wazuh-docker-tmp ] && rm -rf wazuh-docker-tmp; \
  git clone --quiet --depth 1 --branch v${WAZUH_VERSION} https://github.com/wazuh/wazuh-docker.git wazuh-docker-tmp && \
  cp -rn wazuh-docker-tmp/single-node/config/. $REMOTE_DIR/config/ 2>/dev/null || true && \
  rm -rf wazuh-docker-tmp"
echo "✓ Config files in place"

# ── 4. Deploy ─────────────────────────────────────────────────────────────────
echo ""
echo "Deploying Wazuh to $HOST..."
ssh "root@$HOST" "mkdir -p $REMOTE_DIR"
scp compose.yml .env "root@$HOST:$REMOTE_DIR/"
ssh "root@$HOST" "cd $REMOTE_DIR && docker compose up -d"

# ── 5. Health check (Wazuh takes 2-3 min to fully start) ─────────────────────
echo ""
echo "Waiting for Wazuh dashboard to become ready (this takes 2-3 minutes)..."
for i in $(seq 1 36); do
  if curl -sfk https://$HOST:8443 > /dev/null 2>&1; then
    echo "✓ Wazuh is up at https://wazuh.yourdomain.com (→ 192.168.x.47:8443)"
    echo "  Login: admin / (your INDEXER_PASSWORD)"
    exit 0
  fi
  echo "  Attempt $i/36 — waiting..."
  sleep 10
done
echo "⚠ Wazuh did not respond on port 8443 after 6 minutes"
echo "  Check: ssh root@$HOST 'docker logs wazuh-dashboard --tail 30'"
