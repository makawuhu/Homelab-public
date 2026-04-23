#!/usr/bin/env bash
# Collect pending apt upgrades from all hosts, emit JSON per host.
# Output: $RUN_DIR/raw/<hostname>.json
set -euo pipefail

RUN_DIR="${1:?Usage: collect.sh <run-dir>}"
mkdir -p "$RUN_DIR/raw"

# name:ip pairs
HOSTS=(
  "pve:192.168.x.4"
  "ct102-claude-ops:127.0.0.1"
  "ct104-nginxproxymanager:192.168.x.31"
  "ct112-iperf3:192.168.x.33"
  "ct122-wazuh:192.168.x.47"
  "ct123-gitea:192.168.x.48"
  "ct124-authelia:192.168.x.49"
)

REMOTE_CMD='apt-get update -qq 2>/dev/null; apt list --upgradable 2>/dev/null | grep "\[upgradable"'

for entry in "${HOSTS[@]}"; do
  name="${entry%%:*}"
  ip="${entry##*:}"
  ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  out_file="$RUN_DIR/raw/${name}.json"
  raw_file="$RUN_DIR/raw/${name}.raw"

  echo "  collecting $name ($ip)..."

  status="ok"
  ssh -o ConnectTimeout=8 -o BatchMode=yes -o StrictHostKeyChecking=no \
    "root@${ip}" "$REMOTE_CMD" > "$raw_file" 2>/dev/null || status="unreachable"

  python3 - "$name" "$ip" "$ts" "$status" "$raw_file" > "$out_file" << 'PYEOF'
import sys, json, re

host, ip, ts, status, raw_file = sys.argv[1:]
packages = []

if status == "ok":
    with open(raw_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Format: name/repo version arch [upgradable from: old_version]
            m = re.match(r'^(\S+?)/\S+\s+(\S+)\s+(\S+)\s+\[upgradable from: (\S+)\]', line)
            if m:
                packages.append({
                    "name": m.group(1),
                    "candidate": m.group(2),
                    "arch": m.group(3),
                    "installed": m.group(4),
                })

result = {
    "host": host,
    "ip": ip,
    "collected_at": ts,
    "status": "up-to-date" if (status == "ok" and not packages) else status,
    "packages": packages
}
print(json.dumps(result, indent=2))
PYEOF

  rm -f "$raw_file"
done

echo "Collection complete — results in $RUN_DIR/raw/"
