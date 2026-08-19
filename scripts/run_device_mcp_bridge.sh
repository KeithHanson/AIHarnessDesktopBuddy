#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$ROOT_DIR/.venv/bin/python" "$ROOT_DIR/host/mcp_server.py" --device-url "http://192.168.1.164" --transport stdio
