#!/usr/bin/env bash
# Create a Gitea branch, commit patch manifests, and open a PR.
# Usage: gitea-pr.sh <run-id> <classified-dir> <pr-body-file>
set -euo pipefail

eval "$(SOPS_AGE_KEY_FILE=/root/.age/key.txt /usr/local/bin/sops --decrypt --input-type dotenv --output-type dotenv /root/homelab/secrets/gitea.sops)"

RUN_ID="${1:?Usage: gitea-pr.sh <run-id> <classified-dir> <pr-body-file>}"
CLASSIFIED_DIR="${2:?}"
PR_BODY_FILE="${3:?}"
BRANCH="patch/${RUN_ID}"
DATE=$(echo "$RUN_ID" | cut -c1-8)

# Check for existing open PR on this branch
existing=$(curl -s \
  -H "Authorization: token $GITEA_TOKEN" \
  "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/pulls?state=open&head=${BRANCH}&limit=1" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['number'] if d else '')" 2>/dev/null)

if [[ -n "$existing" ]]; then
  echo "PR already exists for branch $BRANCH (#$existing) — skipping."
  exit 0
fi

# Create branch from main
echo "Creating branch $BRANCH..."
curl -s -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/branches" \
  -H "Authorization: token $GITEA_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"new_branch_name\": \"$BRANCH\", \"old_branch_name\": \"main\"}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('  branch created:', d.get('name','ERROR'))"

# Commit each classified manifest to patches/pending/
for manifest in "$CLASSIFIED_DIR"/*.yml; do
  fname=$(basename "$manifest")
  host="${fname%.yml}"
  remote_path="patches/pending/${RUN_ID}-${host}.yml"
  content=$(base64 -w0 "$manifest")

  echo "  committing $remote_path..."
  curl -s -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/contents/${remote_path}" \
    -H "Authorization: token $GITEA_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"message\": \"chore: patch manifest ${RUN_ID} for ${host}\",
      \"content\": \"${content}\",
      \"branch\": \"${BRANCH}\"
    }" | python3 -c "import sys,json; d=json.load(sys.stdin); print('  committed:', d.get('content',{}).get('name','ERROR'))"
done

# Count hosts with pending review
n_hosts=$(ls "$CLASSIFIED_DIR"/*.yml | wc -l)
pr_body=$(cat "$PR_BODY_FILE")

# Open PR
echo "Opening PR..."
pr_number=$(curl -s -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/pulls" \
  -H "Authorization: token $GITEA_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"[patch] ${DATE} — ${n_hosts} host(s) need review\",
    \"body\": $(echo "$pr_body" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))"),
    \"head\": \"${BRANCH}\",
    \"base\": \"main\"
  }" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('number','ERROR'))")

echo "PR #${pr_number} opened: ${GITEA_URL}/${GITEA_REPO}/pulls/${pr_number}"
