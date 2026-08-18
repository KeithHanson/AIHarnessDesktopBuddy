#!/usr/bin/env bash
set -euo pipefail
python3 "$(cd "$(dirname "$0")" && pwd)/restart_and_logs.py" "${1:-/dev/ttyACM0}"
