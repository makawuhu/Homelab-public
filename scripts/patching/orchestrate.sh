#!/usr/bin/env bash
# Patch management orchestrator.
# Collects, classifies, auto-applies safe patches, opens Gitea PR for risky ones.
#
# Usage: orchestrate.sh [--dry-run] [--host <name>] [--force-review]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
POLICY="$REPO_DIR/scripts/patch-policy.yml"

DRY_RUN=false
FORCE_REVIEW=false
TARGET_HOST=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)      DRY_RUN=true ;;
    --force-review) FORCE_REVIEW=true ;;
    --host)         TARGET_HOST="$2"; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
  shift
done

RUN_ID="$(date +%Y%m%d)-$(openssl rand -hex 3)"
RUN_DIR="/tmp/patch-run-${RUN_ID}"
DATE="$(date +%Y-%m-%d)"
LOG="/var/log/patch-orchestrator.log"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG"; }

log "=== Patch run $RUN_ID starting (dry-run=$DRY_RUN) ==="
mkdir -p "$RUN_DIR"

# --- Collect ---
log "Collecting package lists..."
bash "$SCRIPT_DIR/collect.sh" "$RUN_DIR"

# Filter to target host if specified
if [[ -n "$TARGET_HOST" ]]; then
  for f in "$RUN_DIR/raw/"*.json; do
    host=$(python3 -c "import json; print(json.load(open('$f'))['host'])")
    if [[ "$host" != "$TARGET_HOST" ]]; then
      rm "$f"
    fi
  done
fi

# --- Classify ---
log "Classifying packages..."
python3 "$SCRIPT_DIR/classify.py" --run-dir "$RUN_DIR" --policy "$POLICY"

if [[ "$FORCE_REVIEW" == "true" ]]; then
  log "FORCE_REVIEW: moving all auto packages to needs-review"
  python3 - "$RUN_DIR/classified" <<'PYEOF'
import os, sys, yaml
d = sys.argv[1]
for fname in os.listdir(d):
    path = os.path.join(d, fname)
    with open(path) as f:
        m = yaml.safe_load(f)
    m['needs_review'] = m.get('needs_review', []) + m.get('auto', [])
    m['auto'] = []
    for p in m['needs_review']:
        p['action'] = 'needs-review'
    with open(path, 'w') as f:
        yaml.dump(m, f, default_flow_style=False, sort_keys=False)
PYEOF
fi

# --- Dry run: print and exit ---
if [[ "$DRY_RUN" == "true" ]]; then
  log "Dry run — classified manifests:"
  for f in "$RUN_DIR/classified/"*.yml; do
    echo "--- $(basename $f) ---"
    cat "$f"
    echo
  done
  rm -rf "$RUN_DIR"
  exit 0
fi

# --- Auto-apply ---
AUTO_REPORT=""
AUTO_COUNT=0

for manifest in "$RUN_DIR/classified/"*.yml; do
  host=$(python3 -c "import yaml; m=yaml.safe_load(open('$manifest')); print(m['host'])")
  auto_pkgs=$(python3 -c "import yaml; m=yaml.safe_load(open('$manifest')); print(len(m.get('auto',[])))")

  if [[ "$auto_pkgs" -gt 0 ]]; then
    log "Auto-applying $auto_pkgs package(s) on $host..."
    ip=$(python3 -c "import yaml; m=yaml.safe_load(open('$manifest')); print(m['ip'])")
    pkg_names=$(python3 -c "import yaml; m=yaml.safe_load(open('$manifest')); print(' '.join(p['name'] for p in m['auto']))")

    if ssh -o ConnectTimeout=15 -o BatchMode=yes "root@${ip}" \
        "DEBIAN_FRONTEND=noninteractive apt-get install --only-upgrade -y ${pkg_names}" 2>&1; then
      AUTO_REPORT+="$host: applied $auto_pkgs package(s): $pkg_names\n"
      AUTO_COUNT=$((AUTO_COUNT + auto_pkgs))
      log "  $host: auto-apply OK"
    else
      AUTO_REPORT+="$host: FAILED to apply: $pkg_names\n"
      log "  $host: auto-apply FAILED"
    fi
  fi
done

if [[ "$AUTO_COUNT" -gt 0 ]]; then
  log "Sending auto-apply confirmation email..."
  bash "$SCRIPT_DIR/notify.sh" \
    "[homelab] Patch run $DATE — $AUTO_COUNT package(s) auto-applied" \
    "Patch run: $RUN_ID\nDate: $DATE\n\nAuto-applied packages:\n\n${AUTO_REPORT}\n---\nSent by patch orchestrator"
fi

# --- Collect needs-review manifests ---
REVIEW_DIR="$RUN_DIR/review"
mkdir -p "$REVIEW_DIR"
REVIEW_HOSTS=()

for manifest in "$RUN_DIR/classified/"*.yml; do
  review_count=$(python3 -c "import yaml; m=yaml.safe_load(open('$manifest')); print(len(m.get('needs_review',[])))")
  if [[ "$review_count" -gt 0 ]]; then
    host=$(python3 -c "import yaml; m=yaml.safe_load(open('$manifest')); print(m['host'])")
    cp "$manifest" "$REVIEW_DIR/${host}.yml"
    REVIEW_HOSTS+=("$host")
  fi
done

if [[ ${#REVIEW_HOSTS[@]} -eq 0 ]]; then
  log "No packages need review — done."
  rm -rf "$RUN_DIR"
  exit 0
fi

# --- Build PR body ---
PR_BODY_FILE="$RUN_DIR/pr-body.md"
python3 - "$REVIEW_DIR" "$RUN_ID" "$DATE" > "$PR_BODY_FILE" <<'PYEOF'
import os, sys, yaml

review_dir, run_id, date = sys.argv[1], sys.argv[2], sys.argv[3]

lines = [f"## Pending Package Review — {date}", "", f"Patch run ID: `{run_id}`", ""]

for fname in sorted(os.listdir(review_dir)):
    with open(os.path.join(review_dir, fname)) as f:
        m = yaml.safe_load(f)

    host, ip = m['host'], m['ip']
    pkgs = m.get('needs_review', [])
    lines.append(f"### {host} ({ip})")
    lines.append("| Package | Installed | Candidate | Delta | Reason |")
    lines.append("|---------|-----------|-----------|-------|--------|")
    for p in pkgs:
        reason = p.get('reason','').replace('|','\\|')
        lines.append(f"| {p['name']} | {p['installed']} | {p['candidate']} | {p.get('version_delta','')} | {reason} |")
    lines.append("")

lines += [
    "---",
    "**Merge this PR to apply the listed packages.**",
    "The webhook reads `patches/pending/` manifests verbatim — do not edit the YAML files.",
    f"Webhook: `http://192.168.x.8:9000/hooks/patch-apply`"
]

print('\n'.join(lines))
PYEOF

log "Opening Gitea PR for ${#REVIEW_HOSTS[@]} host(s) needing review..."
bash "$SCRIPT_DIR/gitea-pr.sh" "$RUN_ID" "$REVIEW_DIR" "$PR_BODY_FILE"

log "=== Patch run $RUN_ID complete ==="
rm -rf "$RUN_DIR"
