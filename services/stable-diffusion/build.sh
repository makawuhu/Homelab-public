#!/usr/bin/env bash
# Build sd-auto:local image on VM 101 (192.168.x.5)
# This must be run before deploy.sh — the compose file uses the local image.
# Build takes 15-30 min on first run (downloads repos and pip deps).
set -euo pipefail

HOST="192.168.x.5"
REMOTE_DIR="/opt/stable-diffusion/docker"

echo "Copying Dockerfile to $HOST..."
ssh "root@$HOST" "mkdir -p $REMOTE_DIR"
scp Dockerfile "root@$HOST:$REMOTE_DIR/Dockerfile"

echo "Building sd-auto:local on $HOST (this will take a while)..."
ssh "root@$HOST" "docker build -t sd-auto:local $REMOTE_DIR"

echo "Build complete. Run ./deploy.sh to start the container."
