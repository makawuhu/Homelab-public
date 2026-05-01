#!/usr/bin/env bash
# daily-review.sh — Triggers the daily agent review via Telegram DM
#
# Fires once daily at 9am PST / 17:00 UTC (cron on CT 119).
# Sends a prompt to the OpenClaw bot DM (chat ID 639984883), which routes
# it to the agent team. Agents read DAILY_REVIEW.md and handle the rest:
# scanning the roadmap, deduplicating against open Gitea issues, creating
# new issues, and sending a summary back.
#
# This script has one job: send the trigger message. Agents do everything else.
#
# Cron: 0 17 * * * /root/sandbox/homelab/scripts/daily-review.sh >> /var/log/daily-review.log 2>&1

set -euo pipefail

ENV_FILE="/root/homelab/services/claude-ops-sandbox/.env"
CHAT_ID="6399984883"
LOG_TAG="daily-review"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[$LOG_TAG] ERROR: env file not found at $ENV_FILE" >&2
  exit 1
fi

BOT_TOKEN="$(grep '^TELEGRAM_BOT_TOKEN=' "$ENV_FILE" | cut -d= -f2)"

if [[ -z "$BOT_TOKEN" ]]; then
  echo "[$LOG_TAG] ERROR: TELEGRAM_BOT_TOKEN missing from $ENV_FILE" >&2
  exit 1
fi

echo "[$LOG_TAG] Sending daily review trigger..."

RESPONSE="$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -H "Content-Type: application/json" \
  -d "{\"chat_id\": \"${CHAT_ID}\", \"text\": \"Read DAILY_REVIEW.md and follow it strictly.\"}" \
  --max-time 15 2>/dev/null || echo '')"

if echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); exit(0 if d.get('ok') else 1)" 2>/dev/null; then
  echo "[$LOG_TAG] Trigger sent successfully."
else
  echo "[$LOG_TAG] WARNING: Telegram send failed. Response: $RESPONSE" >&2
fi
