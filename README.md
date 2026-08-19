# AIHarnessDesktopBuddy

## 1. Motivation

This project is the bare minimum to get not-annoying alerts that your AI is waiting on you or has a question.

It is meant to be simple:
- a small display
- anything that can run MicroPython
- no voice
- no speakers
- no cameras

The goal is just to have a little fun while trying to avoid having the AI wait on you.

I wanted it to integrate primarily over MCP, but it also exposes a simple HTTP API.

It provides:
- a tiny face renderer for a 128x64 SSD1306 OLED
- a periodic clock/date overlay with configurable interval and duration
- a simple HTTP JSON API on the device
- a minimal MCP-compatible JSON-RPC endpoint on the device
- an optional host-side MCP bridge for stricter MCP clients

## Faces

The project currently includes these animated faces:

| Face | Preview | Use |
|---|---|---|
| `neutral` | ![Neutral face](generated_previews/neutral.gif) | Idle or normal operation |
| `happy` | ![Happy face](generated_previews/happy.gif) | Task completed or system doing well |
| `excited` | ![Excited face](generated_previews/excited.gif) | Celebrations or energetic notifications |
| `sleepy` | ![Sleepy face](generated_previews/sleepy.gif) | Idle for a long time or quiet mode |
| `sad` | ![Sad face](generated_previews/sad.gif) | Failure or blocked actions |
| `confused` | ![Confused face](generated_previews/confused.gif) | Input unclear or more info needed |
| `love` | ![Love face](generated_previews/love.gif) | Affection, praise, or warm social moments |
| `thinking` | ![Thinking face](generated_previews/thinking.gif) | Reading, analysis, or code review |
| `working` | ![Working face](generated_previews/working.gif) | Active work, commands, or long-running tasks |
| `reading` | ![Reading face](generated_previews/reading.gif) | Focused reading or reviewing content |
| `writing` | ![Writing face](generated_previews/writing.gif) | Writing or editing content |
| `waiting` | ![Waiting face](generated_previews/waiting.gif) | Waiting on the operator or for input |
| `subagents` | ![Subagents face](generated_previews/subagents.gif) | Coordinating or monitoring subagents |

## 2. Quickstart: Setup the device and connect it to Wi-Fi

If your ESP32-S3 is wired up and ready to flash, do this first.

### Install the required host tools

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install mpremote esptool pyserial
pip install -r host/requirements.txt
```

Notes:
- `mpremote` is used to copy files and open the REPL.
- `esptool` is used to flash MicroPython firmware.
- `pyserial` is used by the helper restart script.
- `host/requirements.txt` installs the optional host MCP bridge dependencies.

### Flash the MicroPython firmware

```bash
esptool.py --chip esp32s3 --port /dev/ttyACM0 erase_flash
esptool.py --chip esp32s3 --port /dev/ttyACM0 --baud 460800 write_flash -z 0 firmware/ESP32_GENERIC_S3-20260406-v1.28.0.bin
```

If your board is on a different port, replace `/dev/ttyACM0`.

### Configure Wi-Fi

Copy the device config template:

```bash
cp device/config.py.example device/config.py
```

Edit `device/config.py` and set at least:

```python
WIFI_MODE = "sta"
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
WIFI_SECURITY = "wpa2"  # or: "wpa_wpa2", "open"
```

If you prefer access-point mode instead of joining your Wi-Fi, use:

```python
WIFI_MODE = "ap"
AP_SSID = "DesktopBuddy"
AP_PASSWORD = "buddybuddy"
```

Behavior notes:
- On boot, the display shows `connecting` before network setup begins.
- If STA connection fails, the device automatically falls back to AP mode.
- In AP mode, the screen shows the AP name, password, and AP IP address.
- In STA mode, once connected, the built-in LED pulses green.

### Deploy the project files

```bash
./scripts/deploy.sh /dev/ttyACM0
```

## 3. Quickstart: Find your device and point your AI at it

Get the device IP:

```bash
./scripts/device_ip.sh /dev/ttyACM0
```

Test that it is up:

```bash
curl http://<device-ip>/health
curl http://<device-ip>/faces
```

Then point your AI at:

```text
http://<device-ip>/
```

When the device is in STA mode, that root page serves the device `AGENTS.md` instructions for how to connect to and use the remote MCP running on the device.

When the device is in AP mode, that root page serves a simple Wi-Fi setup page. Submitting the form:
- saves the Wi-Fi SSID, password, and security mode
- returns a success page
- soft reboots the device

See the example `AGENTS.md` for how to use it.

## Hardware

- Board: ESP32-S3 Zero
- Display: 0.96" I2C OLED (SSD1306, typically `0x3C`, 128x64)
- Built-in RGB LED: WS2812 on `GP21`

## Suggested wiring

The ESP32-S3 Zero can map I2C to many pins. This project defaults to:

- OLED `VCC` -> `3V3`
- OLED `GND` -> `GND`
- OLED `SCL` -> `GP5`
- OLED `SDA` -> `GP4`

If you use different pins, edit `device/config.py`.

For the clock overlay, you can also optionally set:

- `CLOCK_OVERLAY_ENABLED` - whether the periodic clock overlay starts enabled
- `CLOCK_OVERLAY_INTERVAL_MINUTES` - how often to show the clock overlay (default `5`)
- `CLOCK_OVERLAY_DURATION_SECONDS` - how long to show it each time (default `60`)
- `TIMEZONE_OFFSET_SECONDS` - offset from UTC for display purposes (for example, CDT is `-18000`)
- `NTP_HOST` - NTP server used to sync the device clock on Wi-Fi startup
- `EVENT_HISTORY_LIMIT` - how many completed async event records to retain for status lookup
- `API_IDLE_TIMEOUT_SECONDS` - after this many seconds without API activity, switch to the idle face (`900` / 15 minutes by default, `0` disables)
- `API_IDLE_FACE` - face to show after the API idle timeout elapses

All config values in `device/config.py` can be viewed and updated over the API/MCP. Some changes apply immediately, while hardware/network/bootstrap settings may require a soft reset or redeploy to fully take effect.

## Device API

Base URL: `http://<device-ip>`

### REST endpoints

- `GET /` - device instructions in STA mode, Wi-Fi setup page in AP mode
- `GET /health`
- `GET /state`
- `GET /faces`
- `GET /clock`
- `GET /config`
- `POST /face` with `{ "name": "happy" }`
- `POST /clock` with `{ "enabled": true, "interval_minutes": 5, "duration_seconds": 15 }`
- `POST /clock/show` with `{ "duration_seconds": 15 }`
- `POST /time/sync` with `{}`
- `POST /reload` with `{}`
- `POST /config` with `{ "API_IDLE_TIMEOUT_SECONDS": 900, "API_IDLE_FACE": "sleepy" }`
- `POST /events` with `{ "type": "set_face", "arguments": { "name": "happy" } }`
- `POST /events/batch` with `{ "events": [{ "type": "set_face", "arguments": { "name": "happy" } }, { "type": "led_off" }] }`
- `GET /events/<event-id>`
- `POST /led` with `{ "on": true, "r": 0, "g": 255, "b": 32, "brightness": 0.2 }`
- `POST /led/off` with `{}`
- `POST /wifi-setup` - HTML form submit endpoint used by the AP setup page

Example config update:

```bash
curl -X POST http://<device-ip>/config \
  -H 'Content-Type: application/json' \
  -d '{"API_IDLE_TIMEOUT_SECONDS":900,"API_IDLE_FACE":"sleepy"}'
```

Example clock update:

```bash
curl -X POST http://<device-ip>/clock \
  -H 'Content-Type: application/json' \
  -d '{"interval_minutes":5,"duration_seconds":15}'
```

Example immediate clock display:

```bash
curl -X POST http://<device-ip>/clock/show \
  -H 'Content-Type: application/json' \
  -d '{"duration_seconds":15}'
```

Example manual NTP sync:

```bash
curl -X POST http://<device-ip>/time/sync \
  -H 'Content-Type: application/json' \
  -d '{}'
```

### Minimal MCP endpoint

- `POST /mcp`

Supported methods:

- `initialize`
- `tools/list`
- `tools/call`

Tools exposed:

- `list_faces`
- `set_face` (queued)
- `get_clock`
- `set_clock`
- `show_clock_now`
- `sync_time`
- `set_clock_enabled` (queued)
- `reload_code` (queued)
- `get_config`
- `set_config`
- `submit_event`
- `submit_events`
- `get_event_status`
- `led_on` (queued)
- `led_off` (queued)
- `get_state`

## Layout

- `device/` - files to copy to the ESP32 running MicroPython
- `host/` - optional host-side MCP bridge and API client
- `scripts/make_face_animation.py` - convert an image into an 8-frame OLED face module

## Flash + copy

1. Install MicroPython on the ESP32-S3.
2. Copy everything from `device/` to the board filesystem.
3. Copy `device/config.py.example` to `config.py` and edit Wi-Fi/pins.
4. Reboot the board.

Example with `mpremote`:

```bash
mpremote connect auto fs cp -r device/: \
  && mpremote connect auto reset
```

Then open the REPL/logs:

```bash
mpremote connect auto repl
```

Or use the deploy script:

```bash
./scripts/deploy.sh
# or: ./scripts/deploy.sh /dev/ttyACM0
```

Get the device IP quickly (this restarts the board and prints the fresh IP):

```bash
./scripts/device_ip.sh
# or: ./scripts/device_ip.sh /dev/ttyACM0
```

Run the face/LED demo:

```bash
./scripts/demo.sh
# or: ./scripts/demo.sh /dev/ttyACM0
```

Soft reload the running device code over HTTP:

```bash
./scripts/reload_device.sh
# or: ./scripts/reload_device.sh http://192.168.1.163
```

Serial soft reset helper:

```bash
./scripts/restart.sh
# or: ./scripts/restart.sh /dev/ttyACM0
```

## Host MCP bridge

This project is configured with a project-local MCP server in `.mcp.json` named `AIHarnessDesktopBuddy`.
It connects directly to:

- `http://192.168.1.164/mcp`

Pi can use that project MCP directly after reloading the session.

If you want to run a separate host bridge manually:

```bash
cd host
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python mcp_server.py --device-url http://<device-ip> --transport stdio
```

Optional HTTP transport:

```bash
python mcp_server.py --device-url http://<device-ip> --transport streamable-http --host 127.0.0.1 --port 8765
```

If you add new on-device MCP tools, reload your harness or refresh MCP session metadata so the updated tool list is discovered.

## Creating an 8-frame face animation from an image

The project supports generated animated faces under `device/buddy/generated_faces/`.

Install Pillow locally if needed:

```bash
pip install Pillow
```

Preview how a PNG will look as an 8-frame OLED animation:

```bash
python scripts/preview_face_animation.py /path/to/face.png --name wink-preview
# add --open to open the generated GIF preview
```

Create a face from a PNG (static image or 8-frame horizontal strip):

```bash
python scripts/make_face_animation.py /path/to/face.png \
  --name wink \
  --description "Use for playful acknowledgement."
```

The conversion scripts also support animated GIF/WebP inputs, but PNG is the simplest recommended format.

This writes:

- `device/buddy/generated_faces/wink.py`
- `device/buddy/generated_faces/__init__.py`
- `generated_previews/wink.png`
- `generated_previews/wink.gif`

Then redeploy:

```bash
./scripts/deploy.sh /dev/ttyACM0
```

After deploy, the generated face appears in `GET /faces` and can be selected with the normal `set_face` API.

## Notes

- By default, every 5 minutes, the device shows `HH:MM:SS` and `YYYY-MM-DD` for 60 seconds, then returns to the active face.
- The overlay schedule can be configured with `CLOCK_OVERLAY_ENABLED`, `CLOCK_OVERLAY_INTERVAL_MINUTES`, and `CLOCK_OVERLAY_DURATION_SECONDS`, or at runtime via `GET /clock`, `POST /clock`, `POST /clock/show`, `get_clock`, `set_clock`, `show_clock_now`, and `set_clock_enabled`.
- The clock uses the device RTC, and the STA Wi-Fi path attempts NTP sync during startup.
- If startup sync fails, `GET /clock`, `GET /state`, and manual `sync_time` responses now expose the last sync status and error.
- The default HTTP port is now `80`, so examples omit `:8080` unless you change `HTTP_PORT`.
- In AP fallback mode, visiting `/` opens the captive-style Wi-Fi setup page for entering STA credentials.
- Submitting the Wi-Fi setup form saves `WIFI_SSID`, `WIFI_PASSWORD`, `WIFI_SECURITY`, switches `WIFI_MODE` back to `sta`, returns a success page, and soft reboots the device.
- If no API traffic is received for `API_IDLE_TIMEOUT_SECONDS`, the device automatically switches to `API_IDLE_FACE` until activity resumes.
- Face animations loop continuously.
- The on-device MCP is intentionally minimal to stay MicroPython-friendly.
- `POST /reload` performs a MicroPython soft reset, which restarts `boot.py`/`main.py` without a power cycle.
- `GET /config`, `POST /config`, MCP `get_config`, and MCP `set_config` let you inspect and edit persisted device configuration remotely.
- Config changes are written back to `config.py` on the device.
- REST state-changing endpoints like `POST /face`, `POST /clock`, `POST /reload`, `POST /led`, and `POST /led/off` execute directly on the device.
- MCP state-changing tools like `set_face`, `set_clock_enabled`, `reload_code`, `led_on`, and `led_off` are queued and return quickly with acceptance and an event id.
- `set_clock` updates the clock overlay schedule directly and persists it to `config.py`.
- `show_clock_now` displays the clock immediately for an optional duration.
- `sync_time` manually re-syncs the RTC with NTP and reports the result.
- `POST /events` and MCP `submit_event` also return quickly with acceptance and an event id; use `GET /events/<event-id>` or MCP `get_event_status` to check completion later.
- `POST /events/batch` and MCP `submit_events` queue multiple actions in one request to reduce round-trip overhead.
- The host bridge is the better option for full MCP compatibility.
- If your OLED is `SH1106` instead of `SSD1306`, swap the driver/renderer layer.
