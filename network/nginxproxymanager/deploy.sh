#!/usr/bin/env bash
# nginxproxymanager runs natively on CT 104 (openresty + node, NOT Docker)
# Installed via Proxmox community helper script
set -euo pipefail

HOST="192.168.x.31"
echo "nginxproxymanager (CT 104) is managed as a native service on $HOST"
echo "  Web UI: http://$HOST:81"
echo "  Update: ssh root@$HOST 'bash <(curl -s https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/update-lxc.sh)'"
