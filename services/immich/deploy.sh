#!/bin/bash
# Deploy script for Immich
# This runs automatically when webhook fires

cd "$(dirname "$0")"
docker compose up -d
