#!/bin/bash
# Gitea Branch Protection Configuration
# Run this after the Actions runner is running and the repo is created in Gitea
#
# Usage: GITEA_ADMIN_TOKEN=<token> ./branch-protection.sh [gitea_url] [repo_owner] [repo_name]
#
# Do NOT pass the API token as a positional argument — it will appear in shell
# history and ps output. Set GITEA_ADMIN_TOKEN as an environment variable instead.
#
# Idempotent: safe to re-run. Existing branch protections are deleted before
# re-applying so settings always reflect what's in this script.

set -e

GITEA_URL="${1:-http://192.168.x.48:3010}"
REPO_OWNER="${2:-your-gitea-user}"
REPO_NAME="${3:-homelab}"

# Token must come from environment only — never pass as CLI arg
if [ -z "$GITEA_ADMIN_TOKEN" ]; then
  echo "❌ GITEA_ADMIN_TOKEN environment variable not set"
  echo "Usage: GITEA_ADMIN_TOKEN=<token> $0 [gitea_url] [repo_owner] [repo_name]"
  exit 1
fi

API_TOKEN="$GITEA_ADMIN_TOKEN"

# Apply branch protection for a given branch (idempotent: delete then create)
apply_protection() {
  local BRANCH="$1"
  local PAYLOAD="$2"

  echo "  → Removing existing protection on '$BRANCH' (if any)..."
  curl -s -X DELETE \
    "$GITEA_URL/api/v1/repos/$REPO_OWNER/$REPO_NAME/branch_protections/$BRANCH" \
    -H "Authorization: token $API_TOKEN" > /dev/null || true

  echo "  → Applying protection on '$BRANCH'..."
  curl -s -X POST \
    "$GITEA_URL/api/v1/repos/$REPO_OWNER/$REPO_NAME/branch_protections" \
    -H "Authorization: token $API_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" | jq .
}

echo "🔒 Configuring branch protection for $REPO_OWNER/$REPO_NAME..."

# main branch
apply_protection "main" '{
  "branch_name": "main",
  "enable_push": false,
  "enable_force_push": false,
  "enable_deletion": false,
  "required_approvals": 1,
  "dismiss_stale_approvals": true,
  "require_signed_commits": false,
  "enable_status_check": true,
  "status_check_contexts": ["CI"],
  "block_on_outdated_branch": true,
  "protected_file_patterns": "",
  "unprotected_file_patterns": ""
}'

# dev branch
apply_protection "dev" '{
  "branch_name": "dev",
  "enable_push": false,
  "enable_force_push": false,
  "enable_deletion": false,
  "required_approvals": 1,
  "dismiss_stale_approvals": true,
  "require_signed_commits": false,
  "enable_status_check": true,
  "status_check_contexts": ["CI"],
  "block_on_outdated_branch": true,
  "protected_file_patterns": "",
  "unprotected_file_patterns": ""
}'

echo "✅ Branch protection configured"
