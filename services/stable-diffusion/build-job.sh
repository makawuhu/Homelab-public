#!/usr/bin/env bash
# Build sd-job:local on VM 131 (gpu, 192.168.x.167)
set -euo pipefail

HOST="192.168.x.167"
SSH_USER="root"
REMOTE_DIR="~/sd-job"

echo "Copying files to $HOST..."
scp Dockerfile.job generate.py "$SSH_USER@$HOST:/tmp/"
ssh "$SSH_USER@$HOST" "mkdir -p $REMOTE_DIR && cp /tmp/Dockerfile.job /tmp/generate.py $REMOTE_DIR/"

echo "Building sd-job:local on $HOST..."
ssh "$SSH_USER@$HOST" "docker build -t sd-job:local -f $REMOTE_DIR/Dockerfile.job $REMOTE_DIR 2>&1"

echo "Build complete. Test with: ./test-job.sh"
