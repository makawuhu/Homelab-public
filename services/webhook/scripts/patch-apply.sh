#!/bin/sh
# Webhook handler for patch PR merges.
# $1 = branch name (patch/<RUN_ID>)
set -eu

BRANCH="${1:-}"
REPO="/opt/homelab"
LOG="/var/log/patch-apply.log"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] patch-apply: $*" | tee -a "$LOG"; }

if [ -z "$BRANCH" ]; then
  log "ERROR: no branch name passed"
  exit 1
fi

RUN_ID="${BRANCH#patch/}"
log "Webhook fired for branch $BRANCH (run $RUN_ID)"

# Sync repo to get the merged manifests
cd "$REPO"
git remote set-url origin http://192.168.x.48:3010/your-gitea-user/homelab.git
git fetch origin main
git reset --hard origin/main
log "Repo synced to main"

# Find manifests for this run
MANIFESTS=$(find patches/pending -name "${RUN_ID}-*.yml" 2>/dev/null || true)

if [ -z "$MANIFESTS" ]; then
  log "No manifests found for run $RUN_ID"
  exit 0
fi

REPORT=""
FAILED=0

for manifest in $MANIFESTS; do
  log "Applying $manifest..."
  if python3 /opt/homelab/scripts/patching/apply-patches.sh "$manifest"; then
    host=$(python3 -c "import yaml; m=yaml.safe_load(open('$manifest')); print(m['host'])")
    REPORT="${REPORT}${host}: applied OK\n"
    log "$manifest: OK"
  else
    host=$(python3 -c "import yaml; m=yaml.safe_load(open('$manifest')); print(m['host'])" 2>/dev/null || echo "$manifest")
    REPORT="${REPORT}${host}: FAILED\n"
    FAILED=$((FAILED + 1))
    log "$manifest: FAILED"
  fi
done

# Move applied manifests to patches/applied/
mkdir -p patches/applied
for manifest in $MANIFESTS; do
  mv "$manifest" patches/applied/
done

git add patches/pending patches/applied
git commit -m "chore: mark patch run ${RUN_ID} as applied" || true
git push origin main || log "WARNING: git push failed — applied/ not yet synced to remote"

# Send email report
DATE=$(echo "$RUN_ID" | cut -c1-8)
STATUS=$( [ "$FAILED" -eq 0 ] && echo "SUCCESS" || echo "$FAILED FAILED" )

bash /opt/homelab/scripts/patching/notify.sh \
  "[homelab] Patch run ${DATE} applied — ${STATUS}" \
  "Patch run: ${RUN_ID}\n\nResults:\n${REPORT}\n---\nSent by patch-apply webhook"

log "=== Run $RUN_ID complete (failed=$FAILED) ==="
