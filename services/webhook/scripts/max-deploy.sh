#!/bin/sh
# max-deploy.sh — fires on push to your-gitea-user/max main branch.
# Phase 1 (Claude-gated): notifies Claude via Telegram. No auto-deploy.
# Phase 2: uncomment the deploy block at the bottom.
set -eu

SHA="${1:-unknown}"
MSG="${2:-no message}"
AUTHOR="${3:-unknown}"
REPO="${4:-your-gitea-user/max}"

LOG="/var/log/deploy.log"
GITEA_URL="http://192.168.x.48:3010"
GPU_HOST="192.168.x.167"
GPU_REPO="/opt/gpu-compute"
GITEA_REPO_URL="${GITEA_URL}/your-gitea-user/max.git"
SHORT_SHA=$(echo "$SHA" | cut -c1-8)

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] max-deploy: $*" | tee -a "$LOG"; }

log "Push to ${REPO} — ${SHORT_SHA} by ${AUTHOR}: ${MSG}"

# --- Fetch changed files from Gitea ---
FILES=""
if [ -n "${GITEA_TOKEN:-}" ]; then
    FILES=$(wget -qO- \
        --header="Authorization: token ${GITEA_TOKEN}" \
        "${GITEA_URL}/api/v1/repos/your-gitea-user/max/git/commits/${SHA}" \
        2>/dev/null | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    files = d.get('files', [])
    names = [f.get('filename','') for f in files[:10]]
    print('\n'.join(names))
except Exception:
    pass
" 2>/dev/null || true)
fi

# --- Build Telegram message ---
if [ -n "$FILES" ]; then
    FILE_LIST=$(echo "$FILES" | sed 's/^/  • /')
    TG_MSG="*[max] Push to main*
Commit: \`${SHORT_SHA}\`
Author: ${AUTHOR}
Message: ${MSG}

Changed files:
${FILE_LIST}

_Pending Claude review — deploy not automatic._"
else
    TG_MSG="*[max] Push to main*
Commit: \`${SHORT_SHA}\`
Author: ${AUTHOR}
Message: ${MSG}

_Pending Claude review — deploy not automatic._"
fi

# --- Send Telegram notification ---
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
    wget -qO- "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        --post-data="chat_id=${TELEGRAM_CHAT_ID}&text=${TG_MSG}&parse_mode=Markdown" \
        > /dev/null 2>&1 && log "Telegram notification sent" || log "WARNING: Telegram notification failed"
else
    log "WARNING: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set — skipping notification"
fi

log "Done (Claude-gated — no auto-deploy)"

# =============================================================================
# PHASE 2: Auto-deploy (uncomment when ready)
# =============================================================================
# log "Deploying to VM 131..."
# if ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
#     root@${GPU_HOST} "
#     set -e
#     if [ ! -d '${GPU_REPO}/.git' ]; then
#         git clone '${GITEA_REPO_URL}' '${GPU_REPO}'
#     fi
#     cd '${GPU_REPO}'
#     git fetch origin main
#     git reset --hard origin/main
#     docker compose up -d --build --remove-orphans
# " 2>&1 | tee -a "$LOG"; then
#     log "Deploy OK"
# else
#     log "Deploy FAILED"
# fi
# =============================================================================
