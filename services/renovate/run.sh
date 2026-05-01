#!/usr/bin/env bash
# Wrapper called by cron. Sources secrets and runs Renovate one-shot.
# Migrated from CT 102 to CT 103 on 2026-04-19.
set -euo pipefail

LOG="/var/log/renovate.log"
log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] renovate: $*" | tee -a "$LOG"; }

eval "$(SOPS_AGE_KEY_FILE=/root/.age/key.txt /usr/local/bin/sops --decrypt --input-type dotenv --output-type dotenv /root/homelab/secrets/renovate.sops)"

RENOVATE_JSON_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/renovate.json"

log "Starting Renovate run..."

# Remove any stale renovate-run container from a previous failed run
docker rm -f renovate-run 2>/dev/null || true

docker pull renovate/renovate:38 2>&1 | tee -a "$LOG" || log "WARNING: pull failed, using cached image"

RENOVATE_WORK=$(mktemp -d /tmp/renovate-work.XXXXXX)
chown 1000:1000 "$RENOVATE_WORK"
trap 'rm -rf "$RENOVATE_WORK"' EXIT

docker run --rm \
  --name renovate-run \
  --security-opt apparmor=unconfined \
  -v "${RENOVATE_WORK}:/tmp/renovate" \
  -v "${RENOVATE_JSON_PATH}:/usr/src/app/renovate.json:ro" \
  -e RENOVATE_PLATFORM=gitea \
  -e RENOVATE_ENDPOINT=http://192.168.x.48:3010 \
  -e RENOVATE_TOKEN="${RENOVATE_TOKEN}" \
  -e RENOVATE_GIT_AUTHOR="Renovate Bot <renovate-bot@yourdomain.com>" \
  -e RENOVATE_ONBOARDING=false \
  -e RENOVATE_REQUIRE_CONFIG=optional \
  -e RENOVATE_CONFIG_FILE=/usr/src/app/renovate.json \
  -e LOG_LEVEL=info \
  -e RENOVATE_CACHE_DIR=/tmp/renovate/cache \
  renovate/renovate:38 \
  your-gitea-user/homelab 2>&1 | tee -a "$LOG"

EXIT_CODE=${PIPESTATUS[0]}
log "Renovate run complete (exit ${EXIT_CODE})"
exit $EXIT_CODE