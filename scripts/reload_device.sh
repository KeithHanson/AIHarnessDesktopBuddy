#!/usr/bin/env bash
set -euo pipefail
DEVICE_URL="${1:-http://192.168.1.163:8080}"
curl -sS -X POST "$DEVICE_URL/reload" \
  -H 'Content-Type: application/json' \
  -d '{}'
printf '\n'
