#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEVICE_DIR="$ROOT_DIR/device"
PORT="${1:-auto}"

if ! command -v mpremote >/dev/null 2>&1; then
  echo "error: mpremote is not installed"
  echo "install with: pip install mpremote"
  exit 1
fi

if [ ! -f "$DEVICE_DIR/config.py" ]; then
  if [ -f "$DEVICE_DIR/config.py.example" ]; then
    cp "$DEVICE_DIR/config.py.example" "$DEVICE_DIR/config.py"
    echo "created $DEVICE_DIR/config.py from example"
    echo "edit it, then run this script again"
    exit 1
  else
    echo "error: missing $DEVICE_DIR/config.py"
    exit 1
  fi
fi

echo "deploying to port: $PORT"

# Root files MicroPython auto-loads from the filesystem root.
mpremote connect "$PORT" fs cp "$DEVICE_DIR/boot.py" :boot.py
mpremote connect "$PORT" fs cp "$DEVICE_DIR/main.py" :main.py
mpremote connect "$PORT" fs cp "$DEVICE_DIR/config.py" :config.py

# Package directories.
mpremote connect "$PORT" fs mkdir :buddy >/dev/null 2>&1 || true
mpremote connect "$PORT" fs mkdir :buddy/generated_faces >/dev/null 2>&1 || true
mpremote connect "$PORT" fs mkdir :lib >/dev/null 2>&1 || true
for f in "$DEVICE_DIR"/buddy/*.py; do
  mpremote connect "$PORT" fs cp "$f" ":buddy/$(basename "$f")"
done
for f in "$DEVICE_DIR"/buddy/generated_faces/*.py; do
  mpremote connect "$PORT" fs cp "$f" ":buddy/generated_faces/$(basename "$f")"
done
for f in "$DEVICE_DIR"/lib/*; do
  mpremote connect "$PORT" fs cp "$f" ":lib/$(basename "$f")"
done

mpremote connect "$PORT" reset

echo
printf 'deployed successfully to %s\n' "$PORT"
echo "root files on device: boot.py, main.py, config.py"
echo "open REPL with: mpremote connect $PORT repl"
