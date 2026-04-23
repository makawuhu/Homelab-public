#!/bin/sh
# GitOps webhook handler — fires on merge to main.
# Runs on CT 102 (claude-ops).
# Sequential: sync repo → apply patches → deploy changed services.
set -eu

REPO="/opt/homelab"
GITEA_URL="http://192.168.x.48:3010/your-gitea-user/homelab.git"
LOG="/var/log/deploy.log"
SELF_IP="192.168.x.8"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] webhook: $*" | tee -a "$LOG"; }

# --- Phase 0: Sync repo ---
log "Syncing repo..."
cd "$REPO"

OLD_HEAD=$(git rev-parse HEAD 2>/dev/null || echo "")
git fetch origin main
git reset --hard origin/main
NEW_HEAD=$(git rev-parse HEAD)
log "Synced $OLD_HEAD -> $NEW_HEAD"

# --- Phase 1: Apply pending patches ---
PATCH_DIR="${REPO}/patches/pending"
if [ -d "$PATCH_DIR" ] && [ "$(ls -A "$PATCH_DIR" 2>/dev/null)" ]; then
    log "Checking for pending patches..."
    for manifest in "$PATCH_DIR"/*.yml; do
        [ -f "$manifest" ] || continue
        RUN_ID=$(basename "$manifest" | sed 's/-.*//')
        log "Applying patch $manifest..."
        if python3 /opt/homelab/scripts/patching/apply-patches.sh "$manifest"; then
            host=$(python3 -c "import yaml; m=yaml.safe_load(open('$manifest')); print(m['host'])" 2>/dev/null || echo "unknown")
            log "Patch $manifest: OK ($host)"
            mkdir -p "${REPO}/patches/applied"
            mv "$manifest" "${REPO}/patches/applied/"
        else
            host=$(python3 -c "import yaml; m=yaml.safe_load(open('$manifest')); print(m['host'])" 2>/dev/null || echo "$manifest")
            log "Patch $manifest: FAILED ($host)"
        fi
    done
    # Commit applied patches
    cd "$REPO"
    git add patches/pending patches/applied 2>/dev/null || true
    git commit -m "chore: mark patches as applied" || true
    git push origin main || log "WARNING: git push failed — applied/ not synced"
else
    log "No pending patches"
fi

# --- Phase 2: Deploy changed services ---
if [ -n "$OLD_HEAD" ] && [ "$OLD_HEAD" != "$NEW_HEAD" ]; then
    CHANGED_SERVICES=$(git diff "${OLD_HEAD}..${NEW_HEAD}" --name-only | grep '^services/' | cut -d/ -f2 | sort -u || true)
else
    CHANGED_SERVICES=""
    log "No HEAD change detected — nothing to deploy"
fi

REPORT=""
FAILED=0

for name in $CHANGED_SERVICES; do
    deploy_file="${REPO}/services/${name}/.deploy"
    compose_path="services/${name}/compose.yml"

    if [ ! -f "$deploy_file" ]; then continue; fi
    if [ ! -f "${REPO}/${compose_path}" ]; then continue; fi

    # Never deploy the webhook service itself — would restart its own container
    if [ "$name" = "webhook" ]; then
        log "Skipping webhook self-deploy (would restart own container)"
        continue
    fi

    HOST=$(grep '^HOST=' "$deploy_file" | cut -d= -f2 | tr -d '[:space:]')
    SSH_USER=$(grep '^SSH_USER=' "$deploy_file" 2>/dev/null | cut -d= -f2 | tr -d '[:space:]' || echo "root")
    REMOTE_REPO=$(grep '^REPO=' "$deploy_file" 2>/dev/null | cut -d= -f2 | tr -d '[:space:]' || echo "/opt/homelab")
    BUILD=$(grep '^BUILD=' "$deploy_file" 2>/dev/null | cut -d= -f2 | tr -d '[:space:]' || echo "false")
    SOURCE_PATH=$(grep '^SOURCE_PATH=' "$deploy_file" 2>/dev/null | cut -d= -f2 | tr -d '[:space:]' || echo "")
    COMPOSE_FILE=$(grep '^COMPOSE_FILE=' "$deploy_file" 2>/dev/null | cut -d= -f2 | tr -d '[:space:]' || echo "compose.yml")
    GITEA_REPO_PATH=$(grep '^GITEA_REPO=' "$deploy_file" 2>/dev/null | cut -d= -f2 | tr -d '[:space:]' || echo "")
    GITHUB_REPO_URL=$(grep '^GITHUB_REPO=' "$deploy_file" 2>/dev/null | cut -d= -f2 | tr -d '[:space:]' || echo "")

    # Decrypt secrets if needed
    if [ -f "${REPO}/services/${name}/.env.sops" ]; then
        log "Decrypting secrets for ${name}..."
        SOPS_AGE_KEY_FILE=/root/.age/key.txt /usr/local/bin/sops --decrypt \
            --input-type dotenv --output-type dotenv \
            "${REPO}/services/${name}/.env.sops" \
            > "${REPO}/services/${name}/.env"
        if [ "$HOST" != "$SELF_IP" ]; then
            scp -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no \
                "${REPO}/services/${name}/.env" \
                "${SSH_USER}@${HOST}:${REMOTE_REPO}/services/${name}/.env"
            rm -f "${REPO}/services/${name}/.env"
        fi
    fi

    # --- Local deploy (self) ---
    if [ "$HOST" = "$SELF_IP" ]; then
        log "Deploying ${name} locally..."
        SERVICE_DIR="${REPO}/services/${name}"
        cd "$SERVICE_DIR"
        COMPOSE_FILE="compose.yml"
        if [ "${BUILD}" = "true" ] && [ -n "${SOURCE_PATH}" ]; then
            if [ -n "$GITEA_REPO_PATH" ]; then
                GITEA_TOKEN=$(SOPS_AGE_KEY_FILE=/root/.age/key.txt /usr/local/bin/sops --decrypt --input-type dotenv --output-type dotenv /opt/homelab/secrets/gitea.sops | grep '^GITEA_TOKEN=' | cut -d= -f2 | tr -d '[:space:]')
                SOURCE_REPO_URL="http://your-gitea-user:${GITEA_TOKEN}@192.168.x.48:3010/${GITEA_REPO_PATH}.git"
            elif [ -n "$GITHUB_REPO_URL" ]; then
                SOURCE_REPO_URL="$GITHUB_REPO_URL"
            fi
            if [ ! -d "${SOURCE_PATH}/.git" ]; then
                git clone "${SOURCE_REPO_URL}" "${SOURCE_PATH}"
            else
                git -C "${SOURCE_PATH}" pull
            fi
            docker compose -f "$COMPOSE_FILE" up --build -d --remove-orphans 2>&1 | tee -a "$LOG"
        elif [ -f "${SERVICE_DIR}/Dockerfile" ]; then
            docker compose -f "$COMPOSE_FILE" up --build -d --remove-orphans 2>&1 | tee -a "$LOG"
        else
            docker compose -f "$COMPOSE_FILE" pull --quiet 2>&1 | tee -a "$LOG"
            docker compose -f "$COMPOSE_FILE" up -d --remove-orphans 2>&1 | tee -a "$LOG"
        fi
        log "${name} (local): OK"
        REPORT="${REPORT}  ${name} (local): OK\n"

    # --- Remote deploy (SSH) ---
    else
        log "Deploying ${name} to ${SSH_USER}@${HOST}..."
        if [ "${REMOTE_REPO}" = "/opt/homelab" ]; then
            # Standard homelab repo — git pull on remote
            if ssh -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
                "${SSH_USER}@${HOST}" "
                set -e
                if [ ! -d '${REMOTE_REPO}' ]; then
                    git clone '${GITEA_URL}' '${REMOTE_REPO}'
                fi
                cd '${REMOTE_REPO}'
                git fetch origin main
                git reset --hard origin/main
                docker compose -f '${compose_path}' pull --quiet
                docker compose -f '${compose_path}' up -d --remove-orphans
            " 2>&1 | tee -a "$LOG"; then
                log "${name} (${SSH_USER}@${HOST}): OK"
                REPORT="${REPORT}  ${name} (${SSH_USER}@${HOST}): OK\n"
            else
                log "${name} (${SSH_USER}@${HOST}): FAILED"
                REPORT="${REPORT}  ${name} (${SSH_USER}@${HOST}): FAILED\n"
                FAILED=$((FAILED + 1))
            fi
        else
            # Custom repo path — scp compose file directly
            REMOTE_COMPOSE_DIR="${REMOTE_REPO}"
            ssh -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
                "${SSH_USER}@${HOST}" "mkdir -p ${REMOTE_COMPOSE_DIR}" 2>/dev/null
            scp -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no \
                "${REPO}/${compose_path}" "${SSH_USER}@${HOST}:${REMOTE_COMPOSE_DIR}/${COMPOSE_FILE}" 2>&1 | tee -a "$LOG"
            if ssh -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
                "${SSH_USER}@${HOST}" "
                set -e
                cd '${REMOTE_COMPOSE_DIR}'
                sudo docker compose -f '${COMPOSE_FILE}' pull --quiet
                sudo docker compose -f '${COMPOSE_FILE}' up -d --remove-orphans
            " 2>&1 | tee -a "$LOG"; then
                log "${name} (${SSH_USER}@${HOST}): OK"
                REPORT="${REPORT}  ${name} (${SSH_USER}@${HOST}): OK\n"
            else
                log "${name} (${SSH_USER}@${HOST}): FAILED"
                REPORT="${REPORT}  ${name} (${SSH_USER}@${HOST}): FAILED\n"
                FAILED=$((FAILED + 1))
            fi
        fi
    fi
done

if [ -z "$REPORT" ]; then
    log "No services deployed."
    exit 0
fi

STATUS=$( [ "$FAILED" -eq 0 ] && echo "SUCCESS" || echo "${FAILED} FAILED" )
log "=== Deploy complete (${STATUS}) ==="