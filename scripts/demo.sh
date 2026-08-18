#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${1:-/dev/ttyACM0}"
IP="$($ROOT_DIR/scripts/device_ip.sh "$PORT" | tr -d '\r\n')"
BASE_URL="http://$IP:8080"
FACES_JSON="/tmp/AIHarnessDesktopBuddy-faces.json"

echo "device ip: $IP"
echo "waiting for API to come up..."
for _ in $(seq 1 20); do
  if curl -fsS "$BASE_URL/health" >/tmp/AIHarnessDesktopBuddy-health.json 2>/dev/null; then
    break
  fi
  sleep 1
done

echo "health:"
cat /tmp/AIHarnessDesktopBuddy-health.json
rm -f /tmp/AIHarnessDesktopBuddy-health.json
echo

echo "faces:"
curl -sS "$BASE_URL/faces" | tee "$FACES_JSON"
echo

echo "initial state:"
curl -sS "$BASE_URL/state"
echo

python3 - "$FACES_JSON" <<'PY' | while IFS='|' read -r face r g b; do
import json, sys
colors = [
    (255, 64, 64),
    (255, 160, 64),
    (255, 255, 64),
    (64, 255, 64),
    (64, 255, 200),
    (64, 160, 255),
    (160, 64, 255),
    (255, 64, 200),
]
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    data = json.load(f)
faces = [item.get('name') for item in data.get('faces', []) if item.get('name')]
for i, name in enumerate(faces):
    r, g, b = colors[i % len(colors)]
    print(f"{name}|{r}|{g}|{b}")
PY
  echo "setting face: $face with led rgb($r,$g,$b)"
  curl -sS -X POST "$BASE_URL/led" \
    -H 'Content-Type: application/json' \
    -d "{\"on\":true,\"r\":$r,\"g\":$g,\"b\":$b,\"brightness\":0.2}"
  echo
  curl -sS -X POST "$BASE_URL/face" \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"$face\"}"
  echo
  sleep 5
done
rm -f "$FACES_JSON"

echo "turning led off"
curl -sS -X POST "$BASE_URL/led/off" \
  -H 'Content-Type: application/json' \
  -d '{}'
echo

echo "final state:"
curl -sS "$BASE_URL/state"
echo
