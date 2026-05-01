#!/usr/bin/env bash
# Download SD 1.5 pruned safetensors to /opt/models on VM 131
set -euo pipefail

HOST="192.168.x.167"
SSH_USER="root"
MODEL_URL="https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors"
DEST="/opt/models/v1-5-pruned-emaonly.safetensors"

echo "Downloading SD 1.5 to $HOST:$DEST (~4GB, this will take a while)..."
ssh "$SSH_USER@$HOST" "wget -c -O $DEST \"$MODEL_URL\""
echo "Done. Model at $DEST"
