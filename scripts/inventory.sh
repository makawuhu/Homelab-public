#!/usr/bin/env bash
# Regenerate homelab inventory by querying the Proxmox host
set -euo pipefail

PVE_HOST="root@192.168.x.4"

echo "# Homelab Quick Status"
echo "_Generated: $(date)_"
echo ""
echo "## LXCs"
ssh "$PVE_HOST" "pvesh get /nodes/pve/lxc --output-format json" | \
  python3 -c "import json,sys; data=json.load(sys.stdin); [print(f\"{r['vmid']:4} {r['name']:<25} {r['status']:<10} mem:{r['mem']//1024//1024}MB/{r['maxmem']//1024//1024}MB\") for r in sorted(data, key=lambda x: x['vmid'])]"

echo ""
echo "## VMs"
ssh "$PVE_HOST" "pvesh get /nodes/pve/qemu --output-format json" | \
  python3 -c "import json,sys; data=json.load(sys.stdin); [print(f\"{r['vmid']:4} {r['name']:<25} {r['status']}\") for r in sorted(data, key=lambda x: x['vmid'])]"

echo ""
echo "## ZFS"
ssh "$PVE_HOST" "zpool list"
