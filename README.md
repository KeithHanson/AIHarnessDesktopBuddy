# AIHarnessDesktopBuddy

A small MicroPython project for an ESP32-S3 Zero with a 0.96" I2C OLED and the onboard WS2812 RGB LED.

It provides:

- a tiny face renderer for a 128x64 SSD1306 OLED
- a simple HTTP JSON API on the device
- a minimal MCP-compatible JSON-RPC endpoint on the device
- an optional host-side MCP bridge for stricter MCP clients

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

## Device API

Base URL: `http://<device-ip>:8080`

### REST endpoints

- `GET /health`
- `GET /state`
- `GET /faces`
- `POST /face` with `{ "name": "happy" }`
- `POST /led` with `{ "on": true, "r": 0, "g": 255, "b": 32, "brightness": 0.2 }`
- `POST /led/off` with `{}`

### Minimal MCP endpoint

- `POST /mcp`

Supported methods:

- `initialize`
- `tools/list`
- `tools/call`

Tools exposed:

- `list_faces`
- `set_face`
- `led_on`
- `led_off`
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

## Host MCP bridge

This project is configured with a project-local MCP server in `.mcp.json` named `AIHarnessDesktopBuddy`.
It connects directly to:

- `http://192.168.1.163:8080/mcp`

Pi can use that project MCP directly after reloading the session.

If you want to run a separate host bridge manually:

```bash
cd host
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python mcp_server.py --device-url http://<device-ip>:8080 --transport stdio
```

Optional HTTP transport:

```bash
python mcp_server.py --device-url http://<device-ip>:8080 --transport streamable-http --host 127.0.0.1 --port 8765
```

## Creating an 8-frame face animation from an image

The project supports generated animated faces under `device/buddy/generated_faces/`.

Install Pillow locally if needed:

```bash
pip install Pillow
```

Preview how an image will look as an 8-frame OLED animation:

```bash
python scripts/preview_face_animation.py /path/to/face.gif --name wink-preview
# add --open to open the generated GIF
```

Create a face from an animated GIF/WebP, a horizontal 8-frame strip, or a static image:

```bash
python scripts/make_face_animation.py /path/to/face.gif \
  --name wink \
  --description "Use for playful acknowledgement."
```

This writes:

- `device/buddy/generated_faces/wink.py`
- `device/buddy/generated_faces/__init__.py`
- `generated_previews/wink.png`
- `generated_previews/wink.gif`

Then redeploy:

```bash
./scripts/deploy.sh /dev/ttyACM0
```

After deploy, the generated face appears in `GET /faces` and can be selected with the normal `set_face` API. Generated faces play their 8 frames once when selected.

## Notes

- Generated faces currently play their 8 frames once when selected as the active face.
- The on-device MCP is intentionally minimal to stay MicroPython-friendly.
- The host bridge is the better option for full MCP compatibility.
- If your OLED is `SH1106` instead of `SSD1306`, swap the driver/renderer layer.
