#!/usr/bin/env bash
# Shared deploy helper functions — source this in service deploy.sh scripts.
# Usage: source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../../scripts/lib/deploy-helpers.sh"
set -euo pipefail

# preflight_ssh <host>
# Verify SSH reachability before starting a deploy. Exits on failure.
preflight_ssh() {
  local host="$1"
  if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "root@$host" true 2>/dev/null; then
    echo "ERROR: Cannot reach root@$host — aborting" >&2
    exit 1
  fi
}

# require_secrets <file...>
# Verify that required secrets files exist before starting a deploy. Exits on first missing file.
require_secrets() {
  for f in "$@"; do
    if [ ! -f "$f" ]; then
      echo "ERROR: Missing secrets file: $f" >&2
      exit 1
    fi
  done
}

# remote_compose_deploy <host> <remote_dir> <compose_src>
# Copy compose_src to host:remote_dir/compose.yml and run docker compose up -d.
remote_compose_deploy() {
  local host="$1" remote_dir="$2" compose_src="$3"
  echo "Deploying to root@$host:$remote_dir..."
  ssh "root@$host" "mkdir -p $remote_dir"
  scp "$compose_src" "root@$host:$remote_dir/compose.yml"
  ssh "root@$host" "cd $remote_dir && docker compose pull --quiet && docker compose up -d"
}

# npm_proxy_upsert <npm_url> <domain> <forward_host> <forward_port> <cert_id>
# Create or update an NPM reverse-proxy entry. Requires NPM_EMAIL and NPM_PASSWORD
# to be set in the environment (source /root/.secrets/npm before calling).
npm_proxy_upsert() {
  local npm_url="$1" domain="$2" forward_host="$3" forward_port="$4" cert_id="$5"

  local token
  token=$(curl -s -X POST "$npm_url/api/tokens" \
    -H "Content-Type: application/json" \
    -d "{\"identity\":\"$NPM_EMAIL\",\"secret\":\"$NPM_PASSWORD\"}" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

  local existing
  existing=$(curl -s "$npm_url/api/nginx/proxy-hosts" \
    -H "Authorization: Bearer $token" \
    | python3 -c "
import sys, json
hosts = json.load(sys.stdin)
match = [h['id'] for h in hosts if '$domain' in h.get('domain_names', [])]
print(match[0] if match else '')
")

  local body="{
    \"domain_names\": [\"$domain\"],
    \"forward_scheme\": \"http\",
    \"forward_host\": \"$forward_host\",
    \"forward_port\": $forward_port,
    \"ssl_forced\": true,
    \"certificate_id\": $cert_id,
    \"http2_support\": true,
    \"block_exploits\": true,
    \"allow_websocket_upgrade\": true,
    \"enabled\": true
  }"

  echo "NPM proxy: $domain → $forward_host:$forward_port..."
  if [ -n "$existing" ]; then
    curl -s -X PUT "$npm_url/api/nginx/proxy-hosts/$existing" \
      -H "Authorization: Bearer $token" \
      -H "Content-Type: application/json" \
      -d "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); print('  Updated proxy (ID', str(d.get('id','?')) + ')')"
  else
    curl -s -X POST "$npm_url/api/nginx/proxy-hosts" \
      -H "Authorization: Bearer $token" \
      -H "Content-Type: application/json" \
      -d "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); print('  Created proxy (ID', str(d.get('id','?')) + ')')"
  fi
}

# unbound_dns_upsert <opnsense_url> <hostname> <domain> <target_ip> <description>
# Add a host override in OPNsense Unbound (skips silently if already present).
# Requires OPN_KEY and OPN_SECRET to be set in the environment
# (source /root/.secrets/opnsense before calling).
unbound_dns_upsert() {
  local opnsense_url="$1" hostname="$2" domain="$3" target_ip="$4" description="$5"

  echo "Unbound DNS: $hostname.$domain → $target_ip..."

  local existing_uuid
  existing_uuid=$(curl -sk -u "$OPN_KEY:$OPN_SECRET" \
    "$opnsense_url/api/unbound/settings/searchHostOverride" \
    | python3 -c "
import sys,json
rows = json.load(sys.stdin).get('rows',[])
match = [r['uuid'] for r in rows if r.get('hostname')=='$hostname' and r.get('domain')=='$domain']
print(match[0] if match else '')
")

  if [ -n "$existing_uuid" ]; then
    echo "  Already exists (UUID $existing_uuid) — skipping."
    return 0
  fi

  curl -sk -u "$OPN_KEY:$OPN_SECRET" \
    -X POST "$opnsense_url/api/unbound/settings/addHostOverride" \
    -H "Content-Type: application/json" \
    -d "{\"host\":{\"hostname\":\"$hostname\",\"domain\":\"$domain\",\"server\":\"$target_ip\",\"description\":\"$description\"}}" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('  Created (UUID', d.get('uuid','?') + ')')"

  curl -sk -u "$OPN_KEY:$OPN_SECRET" \
    -X POST "$opnsense_url/api/unbound/service/reconfigure" \
    -H "Content-Type: application/json" -d '{}' > /dev/null
  echo "  DNS applied."
}

# wait_for_http <url> <tries> <interval_sec> <label>
# Poll <url> until it returns HTTP 2xx. Prints attempt progress.
# Returns 1 if the service does not respond within tries*interval_sec seconds.
wait_for_http() {
  local url="$1" tries="$2" interval="$3" label="$4"
  echo "Waiting for $label..."
  for i in $(seq 1 "$tries"); do
    if curl -sfk "$url" > /dev/null 2>&1; then
      echo "✓ $label is up"
      return 0
    fi
    echo "  Attempt $i/$tries — waiting ${interval}s..."
    sleep "$interval"
  done
  echo "⚠ $label did not respond after $((tries * interval))s" >&2
  return 1
}
