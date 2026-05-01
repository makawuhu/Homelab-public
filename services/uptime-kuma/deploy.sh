#!/bin/bash
# Deploy script for Uptime Kuma
# This runs automatically when webhook fires

cd "$(dirname "$0")"
docker compose up -d
