import json
import socket


def _json_response(status, payload):
    body = json.dumps(payload)
    return (
        "HTTP/1.1 %d OK\r\n" % status
        + "Content-Type: application/json\r\n"
        + "Access-Control-Allow-Origin: *\r\n"
        + "Content-Length: %d\r\n" % len(body)
        + "Connection: close\r\n\r\n"
        + body
    )


def _text_response(status, body, content_type="text/plain; charset=utf-8"):
    return (
        "HTTP/1.1 %d OK\r\n" % status
        + "Content-Type: %s\r\n" % content_type
        + "Access-Control-Allow-Origin: *\r\n"
        + "Content-Length: %d\r\n" % len(body)
        + "Connection: close\r\n\r\n"
        + body
    )


def _read_request(conn):
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = conn.recv(1024)
        if not chunk:
            break
        data += chunk
        if len(data) > 8192:
            break
    if not data:
        return None
    head, _, rest = data.partition(b"\r\n\r\n")
    lines = head.decode().split("\r\n")
    method, path, _ = lines[0].split(" ", 2)
    headers = {}
    for line in lines[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    content_length = int(headers.get("content-length", "0"))
    body = rest
    while len(body) < content_length:
        body += conn.recv(1024)
    return method, path, headers, body


def _percent_decode(text):
    out = []
    i = 0
    length = len(text)
    while i < length:
        ch = text[i]
        if ch == "+":
            out.append(" ")
            i += 1
        elif ch == "%" and i + 2 < length:
            try:
                out.append(chr(int(text[i + 1 : i + 3], 16)))
                i += 3
            except Exception:
                out.append(ch)
                i += 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _parse_form(body):
    text = body.decode() if body else ""
    values = {}
    if not text:
        return values
    for part in text.split("&"):
        if not part:
            continue
        if "=" in part:
            key, value = part.split("=", 1)
        else:
            key, value = part, ""
        values[_percent_decode(key)] = _percent_decode(value)
    return values


class BuddyServer:
    def __init__(self, state, device_name, bind_ip, port):
        self.state = state
        self.device_name = device_name
        self.bind_ip = bind_ip
        self.port = port

    def _agents_md(self):
        return """# AGENTS.md

This device exposes a small HTTP API and a remote MCP-style JSON-RPC endpoint.

## Base URL

- http://<device-ip>:8080

## Health check

- GET /health

## REST API

- GET /faces
- GET /state
- GET /clock
- GET /config
- GET /events/<event-id>
- POST /face with JSON: {\"name\": \"excited\"}
- POST /clock with JSON: {\"enabled\": true}
- POST /reload with JSON: {}
- POST /config with JSON: {\"API_IDLE_TIMEOUT_SECONDS\": 900, \"API_IDLE_FACE\": \"sleepy\"}
- POST /events with JSON: {\"type\": \"set_face\", \"arguments\": {\"name\": \"happy\"}}
- POST /events/batch with JSON: {\"events\": [{\"type\": \"set_face\", \"arguments\": {\"name\": \"happy\"}}, {\"type\": \"led_off\"}]}
- POST /led with JSON: {\"on\": true, \"r\": 0, \"g\": 128, \"b\": 255, \"brightness\": 0.2}
- POST /led/off with JSON: {}

## Remote MCP connectivity

This device exposes MCP-style JSON-RPC over HTTP at:

- POST /mcp

Supported JSON-RPC methods:

- initialize
- tools/list
- tools/call

Available tools:

- list_faces
- set_face
- get_clock
- set_clock_enabled
- reload_code
- get_config
- set_config
- submit_event
- submit_events
- get_event_status
- led_on
- led_off
- get_state

## Example MCP initialize

POST /mcp
Content-Type: application/json

{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{}}

## Example MCP tools/list

POST /mcp
Content-Type: application/json

{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\",\"params\":{}}

## Example MCP tools/call

Set face:

{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":{\"name\":\"set_face\",\"arguments\":{\"name\":\"excited\"}}}

Turn LED on:

{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"led_on\",\"arguments\":{\"r\":0,\"g\":128,\"b\":255,\"brightness\":0.2}}}

Update config:

{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"tools/call\",\"params\":{\"name\":\"set_config\",\"arguments\":{\"updates\":{\"API_IDLE_TIMEOUT_SECONDS\":900}}}}

## Notes

- Generated animated faces are the supported face implementation.
- If a stricter MCP client is needed, run a host-side MCP bridge that forwards to this device.
- The direct on-device MCP endpoint is intentionally minimal and HTTP-based.
"""

    def _selected(self, value, current):
        if value == current:
            return " selected"
        return ""

    def _wifi_setup_page(self, message=None, error=None):
        config = self.state.get_config()["config"]
        ssid = config.get("WIFI_SSID") or ""
        password = config.get("WIFI_PASSWORD") or ""
        security = config.get("WIFI_SECURITY") or "wpa2"
        notice = ""
        if error:
            notice = '<div class="notice error">%s</div>' % error
        elif message:
            notice = '<div class="notice ok">%s</div>' % message
        return """<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
  <title>DesktopBuddy Wi-Fi Setup</title>
  <style>
    body { font-family: sans-serif; background: #111827; color: #f9fafb; margin: 0; padding: 24px; }
    .card { max-width: 420px; margin: 0 auto; background: #1f2937; padding: 20px; border-radius: 12px; }
    h1 { margin-top: 0; font-size: 24px; }
    p { color: #d1d5db; }
    label { display: block; margin: 14px 0 6px; font-weight: 600; }
    input, select, button { width: 100%%; box-sizing: border-box; padding: 12px; border-radius: 8px; border: 1px solid #374151; }
    input, select { background: #111827; color: #f9fafb; }
    button { margin-top: 18px; background: #2563eb; color: white; border: none; font-weight: 700; }
    .notice { padding: 12px; border-radius: 8px; margin-bottom: 16px; }
    .ok { background: #14532d; }
    .error { background: #7f1d1d; }
    .small { font-size: 13px; color: #9ca3af; }
  </style>
</head>
<body>
  <div class=\"card\">
    <h1>DesktopBuddy Wi-Fi Setup</h1>
    <p>Connect this device to your Wi-Fi network. After saving, the device will reboot.</p>
    %s
    <form method=\"post\" action=\"/wifi-setup\">
      <label for=\"ssid\">Wi-Fi name (SSID)</label>
      <input id=\"ssid\" name=\"ssid\" value=\"%s\" required>

      <label for=\"security\">Security</label>
      <select id=\"security\" name=\"security\">
        <option value=\"wpa2\"%s>WPA2 Personal</option>
        <option value=\"wpa_wpa2\"%s>WPA/WPA2 Personal</option>
        <option value=\"open\"%s>Open</option>
      </select>

      <label for=\"password\">Password</label>
      <input id=\"password\" name=\"password\" type=\"password\" value=\"%s\">
      <div class=\"small\">Leave blank for open networks.</div>

      <button type=\"submit\">Save and reboot</button>
    </form>
  </div>
</body>
</html>
""" % (
            notice,
            ssid,
            self._selected("wpa2", security),
            self._selected("wpa_wpa2", security),
            self._selected("open", security),
            password,
        )

    def _wifi_setup_success_page(self):
        return """<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
  <title>DesktopBuddy Wi-Fi Saved</title>
  <style>
    body { font-family: sans-serif; background: #111827; color: #f9fafb; margin: 0; padding: 24px; }
    .card { max-width: 420px; margin: 0 auto; background: #1f2937; padding: 20px; border-radius: 12px; }
    .ok { background: #14532d; padding: 12px; border-radius: 8px; }
  </style>
</head>
<body>
  <div class=\"card\">
    <h1>Success</h1>
    <div class=\"ok\">Wi-Fi settings saved. The device is rebooting now.</div>
  </div>
</body>
</html>
"""

    def _mcp_tools(self):
        return [
            {
                "name": "list_faces",
                "description": "List available face names and when each should be used.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "set_face",
                "description": "Set the current face on the OLED display.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            },
            {
                "name": "get_clock",
                "description": "Get periodic clock overlay settings and visibility state.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "set_clock_enabled",
                "description": "Enable or disable the periodic clock/date overlay.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"enabled": {"type": "boolean"}},
                    "required": ["enabled"],
                },
            },
            {
                "name": "reload_code",
                "description": "Trigger a MicroPython soft reset so updated code is reloaded.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_config",
                "description": "Get the current editable device configuration.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "set_config",
                "description": "Update editable device configuration values and persist them to config.py.",
                "inputSchema": {"type": "object", "properties": {"updates": {"type": "object"}}, "required": ["updates"]},
            },
            {
                "name": "submit_event",
                "description": "Queue an event and return immediately with acceptance plus an event id.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "arguments": {"type": "object"}
                    },
                    "required": ["type"]
                },
            },
            {
                "name": "submit_events",
                "description": "Queue multiple events and return immediately with acceptance plus event ids.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "events": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string"},
                                    "arguments": {"type": "object"}
                                },
                                "required": ["type"]
                            }
                        }
                    },
                    "required": ["events"]
                },
            },
            {
                "name": "get_event_status",
                "description": "Get queued/running/completed/failed status for a previously submitted event.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"event_id": {"type": "string"}},
                    "required": ["event_id"]
                },
            },
            {
                "name": "led_on",
                "description": "Turn on the built-in RGB LED with color and brightness.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "r": {"type": "integer"},
                        "g": {"type": "integer"},
                        "b": {"type": "integer"},
                        "brightness": {"type": "number"},
                    },
                    "required": ["r", "g", "b"],
                },
            },
            {
                "name": "led_off",
                "description": "Turn off the built-in RGB LED.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_state",
                "description": "Get current device face and LED state.",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]

    def _dispatch_tool(self, name, arguments):
        arguments = arguments or {}
        if name == "list_faces":
            return {"faces": self.state.get_faces()}
        if name == "set_face":
            return self.state.submit_event("set_face", {"name": arguments.get("name")})
        if name == "get_clock":
            return {"clock": self.state.get_clock_settings()}
        if name == "set_clock_enabled":
            return self.state.submit_event("set_clock_enabled", {"enabled": arguments.get("enabled")})
        if name == "reload_code":
            return self.state.submit_event("reload_code", {})
        if name == "get_config":
            return self.state.get_config()
        if name == "set_config":
            return self.state.update_config(arguments.get("updates", {}))
        if name == "submit_event":
            return self.state.submit_event(arguments.get("type"), arguments.get("arguments", {}))
        if name == "submit_events":
            return self.state.submit_events(arguments.get("events", []))
        if name == "get_event_status":
            return {"event": self.state.get_event_status(arguments.get("event_id"))}
        if name == "led_on":
            return self.state.submit_event(
                "led_on",
                {
                    "r": arguments.get("r", 0),
                    "g": arguments.get("g", 0),
                    "b": arguments.get("b", 0),
                    "brightness": arguments.get("brightness", 1.0),
                },
            )
        if name == "led_off":
            return self.state.submit_event("led_off", {})
        if name == "get_state":
            return self.state.get_state()
        raise ValueError("unknown tool: %s" % name)

    def _is_ap_mode(self):
        state = self.state.get_state()
        return state.get("boot_info", {}).get("mode") == "ap"

    def _handle_wifi_setup(self, body):
        form = _parse_form(body)
        ssid = (form.get("ssid") or "").strip()
        security = (form.get("security") or "wpa2").strip()
        password = form.get("password") or ""
        if not ssid:
            return 400, self._wifi_setup_page(error="Wi-Fi name is required."), "text/html; charset=utf-8"
        if security not in ("open", "wpa2", "wpa_wpa2"):
            return 400, self._wifi_setup_page(error="Unsupported security type."), "text/html; charset=utf-8"
        if security != "open" and not password:
            return 400, self._wifi_setup_page(error="Password is required for secured networks."), "text/html; charset=utf-8"
        updates = {
            "WIFI_MODE": "sta",
            "WIFI_SSID": ssid,
            "WIFI_PASSWORD": "" if security == "open" else password,
            "WIFI_SECURITY": security,
        }
        self.state.update_config(updates)
        self.state.request_soft_reset()
        return 200, self._wifi_setup_success_page(), "text/html; charset=utf-8"

    def _handle_rest(self, method, path, headers, body):
        payload = {}
        content_type = headers.get("content-type", "")
        if body and content_type.startswith("application/json"):
            payload = json.loads(body.decode() or "{}")
        if method == "GET" and path == "/":
            if self._is_ap_mode():
                return 200, self._wifi_setup_page(), "text/html; charset=utf-8"
            return 200, self._agents_md(), "text/markdown; charset=utf-8"
        if method == "POST" and path == "/wifi-setup":
            return self._handle_wifi_setup(body)
        if method == "GET" and path == "/health":
            return 200, {"ok": True, "device": self.device_name}, "application/json"
        if method == "GET" and path == "/state":
            return 200, self.state.get_state(), "application/json"
        if method == "GET" and path == "/faces":
            return 200, {"faces": self.state.get_faces()}, "application/json"
        if method == "GET" and path == "/clock":
            return 200, {"clock": self.state.get_clock_settings()}, "application/json"
        if method == "GET" and path == "/config":
            return 200, self.state.get_config(), "application/json"
        if method == "GET" and path.startswith("/events/"):
            return 200, {"event": self.state.get_event_status(path[len("/events/") :])}, "application/json"
        if method == "POST" and path == "/face":
            return 200, self.state.set_face(payload.get("name")), "application/json"
        if method == "POST" and path == "/clock":
            return 200, self.state.set_clock_enabled(payload.get("enabled")), "application/json"
        if method == "POST" and path == "/reload":
            return 200, self.state.request_soft_reset(), "application/json"
        if method == "POST" and path == "/config":
            return 200, self.state.update_config(payload), "application/json"
        if method == "POST" and path == "/events":
            return 200, self.state.submit_event(payload.get("type"), payload.get("arguments", {})), "application/json"
        if method == "POST" and path == "/events/batch":
            return 200, self.state.submit_events(payload.get("events", [])), "application/json"
        if method == "POST" and path == "/led":
            if not payload.get("on", True):
                return 200, self.state.led_off(), "application/json"
            return 200, self.state.led_on(
                payload.get("r", 0),
                payload.get("g", 0),
                payload.get("b", 0),
                payload.get("brightness", 1.0),
            ), "application/json"
        if method == "POST" and path == "/led/off":
            return 200, self.state.led_off(), "application/json"
        return 404, {"ok": False, "error": "not found"}, "application/json"

    def _handle_mcp(self, body):
        req = json.loads(body.decode() or "{}")
        method = req.get("method")
        req_id = req.get("id")
        if method == "initialize":
            result = {
                "protocolVersion": "2025-03-26",
                "serverInfo": {"name": self.device_name, "version": "0.1.0"},
                "capabilities": {"tools": {}},
            }
        elif method == "notifications/initialized":
            result = {}
        elif method == "tools/list":
            result = {"tools": self._mcp_tools()}
        elif method == "tools/call":
            params = req.get("params", {})
            out = self._dispatch_tool(params.get("name"), params.get("arguments", {}))
            result = {"content": [{"type": "text", "text": json.dumps(out)}]}
        else:
            return 200, {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": "method not found"},
            }
        return 200, {"jsonrpc": "2.0", "id": req_id, "result": result}

    def serve_forever(self):
        addr = socket.getaddrinfo(self.bind_ip, self.port)[0][-1]
        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(addr)
        sock.listen(2)
        print("buddy server listening on http://%s:%s" % (self.bind_ip, self.port))
        while True:
            conn, _ = sock.accept()
            try:
                req = _read_request(conn)
                if not req:
                    conn.close()
                    continue
                method, path, headers, body = req
                self.state.mark_api_activity()
                if method == "OPTIONS":
                    conn.sendall(_json_response(200, {"ok": True}).encode())
                elif path == "/mcp":
                    status, payload = self._handle_mcp(body)
                    conn.sendall(_json_response(status, payload).encode())
                else:
                    status, payload, content_type = self._handle_rest(method, path, headers, body)
                    if content_type.startswith("application/json"):
                        conn.sendall(_json_response(status, payload).encode())
                    else:
                        conn.sendall(_text_response(status, payload, content_type).encode())
            except Exception as exc:
                err = _json_response(500, {"ok": False, "error": str(exc)})
                conn.sendall(err.encode())
            finally:
                conn.close()
