#!/usr/bin/env bash
# Submit a test SD generation job to khris-gpu
set -euo pipefail

RESPONSE=$(curl -s -X POST https://khris-gpu.yourdomain.com/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "job_type": "custom_docker",
    "timeout_seconds": 120,
    "payload": {
      "image": "sd-job:local",
      "env": {
        "PROMPT": "a photo of a cat sitting on a windowsill, soft lighting",
        "NEGATIVE_PROMPT": "blurry, low quality",
        "STEPS": "20",
        "WIDTH": "512",
        "HEIGHT": "512",
        "MODEL_PATH": "/models/v1-5-pruned-emaonly.safetensors"
      },
      "volumes": {
        "/opt/models": "/models",
        "/opt/outputs": "/output"
      },
      "shm_size": "2g"
    }
  }')

echo "Raw response: $RESPONSE"
JOB_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")
echo "Job submitted: $JOB_ID"
echo "Polling for result..."

while true; do
  STATUS=$(curl -s "https://khris-gpu.yourdomain.com/jobs/$JOB_ID")
  STATE=$(echo "$STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
  if [[ "$STATE" == "completed" ]]; then
    FILENAME=$(echo "$STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['result']['stdout'].strip())")
    echo "Done: https://khris-gpu-outputs.yourdomain.com/$FILENAME"
    break
  elif [[ "$STATE" == "failed" ]]; then
    echo "Failed:"
    echo "$STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['result']['stderr'])"
    exit 1
  fi
  sleep 5
done
