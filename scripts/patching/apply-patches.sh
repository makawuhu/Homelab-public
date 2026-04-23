#!/usr/bin/env bash
# Apply patches from a classified manifest to a remote host.
# Usage: apply-patches.sh <manifest-file>
# Called by the webhook handler after PR merge.
set -euo pipefail

MANIFEST="${1:?Usage: apply-patches.sh <manifest-file>}"

python3 - "$MANIFEST" <<'PYEOF'
import sys, yaml, subprocess, os

manifest_path = sys.argv[1]
with open(manifest_path) as f:
    manifest = yaml.safe_load(f)

host = manifest['host']
ip = manifest['ip']
packages = manifest.get('needs_review', [])

if not packages:
    print(f"  {host}: nothing to apply")
    sys.exit(0)

pkg_names = [p['name'] for p in packages]
pkg_list = ' '.join(pkg_names)
print(f"  {host} ({ip}): applying {len(pkg_names)} package(s): {pkg_list}")

cmd = [
    'ssh', '-o', 'ConnectTimeout=30', '-o', 'BatchMode=yes',
    '-o', 'StrictHostKeyChecking=no',
    f'root@{ip}',
    f'DEBIAN_FRONTEND=noninteractive apt-get install --only-upgrade -y {pkg_list}'
]

result = subprocess.run(cmd, capture_output=True, text=True)

if result.returncode == 0:
    print(f"  {host}: SUCCESS")
    print(result.stdout[-2000:] if result.stdout else '')
else:
    print(f"  {host}: FAILED (exit {result.returncode})")
    print(result.stderr[-2000:] if result.stderr else '')
    sys.exit(1)
PYEOF
