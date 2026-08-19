import json
from urllib import request


class BuddyApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def _get(self, path: str):
        req = request.Request(self.base_url + path, method="GET")
        with request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())

    def _post(self, path: str, payload: dict):
        data = json.dumps(payload).encode()
        req = request.Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())

    def health(self):
        return self._get("/health")

    def state(self):
        return self._get("/state")

    def faces(self):
        return self._get("/faces")

    def set_face(self, name: str):
        return self._post("/face", {"name": name})

    def clock(self):
        return self._get("/clock")

    def set_clock(self, enabled: bool | None = None, interval_minutes: int | None = None, duration_seconds: int | None = None):
        payload = {}
        if enabled is not None:
            payload["enabled"] = enabled
        if interval_minutes is not None:
            payload["interval_minutes"] = interval_minutes
        if duration_seconds is not None:
            payload["duration_seconds"] = duration_seconds
        return self._post("/clock", payload)

    def show_clock_now(self, duration_seconds: int | None = None):
        payload = {}
        if duration_seconds is not None:
            payload["duration_seconds"] = duration_seconds
        return self._post("/clock/show", payload)

    def sync_time(self):
        return self._post("/time/sync", {})

    def set_clock_enabled(self, enabled: bool):
        return self.set_clock(enabled=enabled)

    def reload(self):
        return self._post("/reload", {})

    def config(self):
        return self._get("/config")

    def set_config(self, updates: dict):
        return self._post("/config", updates)

    def submit_event(self, event_type: str, arguments: dict | None = None):
        return self._post("/events", {"type": event_type, "arguments": arguments or {}})

    def submit_events(self, events: list[dict]):
        return self._post("/events/batch", {"events": events})

    def event_status(self, event_id: str):
        return self._get(f"/events/{event_id}")

    def led_on(self, r: int, g: int, b: int, brightness: float = 1.0):
        return self._post("/led", {"on": True, "r": r, "g": g, "b": b, "brightness": brightness})

    def led_off(self):
        return self._post("/led/off", {})
