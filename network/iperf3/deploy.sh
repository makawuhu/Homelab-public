#!/usr/bin/env bash
# iperf3 runs natively on CT 112
set -euo pipefail

HOST="192.168.x.33"
echo "iperf3 (CT 112) is a native service on $HOST"
echo "  Test: iperf3 -c $HOST"
echo "  Server status: ssh root@$HOST 'systemctl status iperf3'"
