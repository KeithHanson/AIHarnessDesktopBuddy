#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${1:-/dev/ttyACM0}"

LOGS="$("$ROOT_DIR/scripts/restart.sh" "$PORT")"
IP="$(printf '%s\n' "$LOGS" | sed -n "s/.*'ip': '\([^']*\)'.*/\1/p" | tail -n 1 | tr -d '\r\n')"

if [ -z "$IP" ]; then
  echo "error: could not determine device IP" >&2
  exit 1
fi

printf '%s\n' "$IP"
