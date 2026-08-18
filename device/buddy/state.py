import _thread
import time
import machine
from buddy.faces import list_faces, get_generated_frames
from buddy.generated_faces import GENERATED_FACES


CONFIG_FIELDS = [
    "DEVICE_NAME",
    "HTTP_PORT",
    "I2C_ID",
    "I2C_SCL_PIN",
    "I2C_SDA_PIN",
    "OLED_WIDTH",
    "OLED_HEIGHT",
    "OLED_ADDR",
    "LED_PIN",
    "LED_COUNT",
    "LED_COLOR_ORDER",
    "LED_PULSE_PERIOD_MS",
    "LED_PULSE_HOLD_OFF_MS",
    "WIFI_MODE",
    "WIFI_SSID",
    "WIFI_PASSWORD",
    "AP_SSID",
    "AP_PASSWORD",
    "CLOCK_OVERLAY_ENABLED",
    "TIMEZONE_OFFSET_SECONDS",
    "NTP_HOST",
    "EVENT_HISTORY_LIMIT",
    "API_IDLE_TIMEOUT_SECONDS",
    "API_IDLE_FACE",
]


class BuddyState:
    def __init__(self, display, led, config=None):
        self.display = display
        self.led = led
        self.config = config
        self.face = "neutral"
        self._display_face = self.face
        self._lock = _thread.allocate_lock()
        self._animation_frames = None
        self._animation_index = 0
        self._animation_delay_ms = 120
        self._clock_visible = False
        self._last_clock_second = None
        self._clock_suppressed_minute = None
        self._clock_enabled = bool(
            getattr(config, "CLOCK_OVERLAY_ENABLED", True)
            if config is not None
            else True
        )
        self._timezone_offset_seconds = int(
            getattr(config, "TIMEZONE_OFFSET_SECONDS", 0)
            if config is not None
            else 0
        )
        self._soft_reset_requested = False
        self._idle_face = getattr(config, "API_IDLE_FACE", "sleepy") if config is not None else "sleepy"
        self._idle_timeout_ms = int(
            getattr(config, "API_IDLE_TIMEOUT_SECONDS", 0)
            if config is not None
            else 0
        ) * 1000
        self._last_activity_ms = time.ticks_ms()
        self._idle_active = False
        self._event_queue = []
        self._event_history = {}
        self._next_event_id = 1
        self._max_event_history = int(
            getattr(config, "EVENT_HISTORY_LIMIT", 32)
            if config is not None
            else 32
        )
        self._apply_runtime_config()
        self.set_face(self.face)

    def get_state(self):
        return {
            "face": self._display_face,
            "selected_face": self.face,
            "led": self.led.state,
            "clock": self.get_clock_settings(),
            "idle": {
                "active": self._idle_active,
                "timeout_seconds": self._idle_timeout_ms // 1000,
                "idle_face": self._idle_face,
            },
            "events": {
                "queued": len(self._event_queue),
                "history": len(self._event_history),
            },
        }

    def _apply_runtime_config(self):
        config = self.config
        self._clock_enabled = bool(getattr(config, "CLOCK_OVERLAY_ENABLED", True))
        self._timezone_offset_seconds = int(getattr(config, "TIMEZONE_OFFSET_SECONDS", 0))
        self._idle_face = getattr(config, "API_IDLE_FACE", "sleepy")
        self._idle_timeout_ms = int(getattr(config, "API_IDLE_TIMEOUT_SECONDS", 0)) * 1000
        self._max_event_history = int(getattr(config, "EVENT_HISTORY_LIMIT", 32))
        if hasattr(self.led, "pulse_period_ms"):
            self.led.pulse_period_ms = int(getattr(config, "LED_PULSE_PERIOD_MS", self.led.pulse_period_ms))
        if hasattr(self.led, "pulse_hold_off_ms"):
            self.led.pulse_hold_off_ms = int(getattr(config, "LED_PULSE_HOLD_OFF_MS", self.led.pulse_hold_off_ms))
        if hasattr(self.led, "color_order"):
            self.led.color_order = getattr(config, "LED_COLOR_ORDER", self.led.color_order).upper()

    def get_config(self):
        config = {}
        for key in CONFIG_FIELDS:
            config[key] = getattr(self.config, key, None)
        return {
            "config": config,
            "runtime": {
                "reload_required_fields": [
                    "DEVICE_NAME",
                    "HTTP_PORT",
                    "I2C_ID",
                    "I2C_SCL_PIN",
                    "I2C_SDA_PIN",
                    "OLED_WIDTH",
                    "OLED_HEIGHT",
                    "OLED_ADDR",
                    "LED_PIN",
                    "LED_COUNT",
                    "WIFI_MODE",
                    "WIFI_SSID",
                    "WIFI_PASSWORD",
                    "AP_SSID",
                    "AP_PASSWORD",
                    "NTP_HOST",
                ],
            },
        }

    def _serialize_config_value(self, value):
        if isinstance(value, str):
            return repr(value)
        if isinstance(value, bool):
            return "True" if value else "False"
        return repr(value)

    def _write_config_file(self):
        lines = ["# Managed by AIHarnessDesktopBuddy runtime configuration.\n", "\n"]
        for key in CONFIG_FIELDS:
            lines.append("%s = %s\n" % (key, self._serialize_config_value(getattr(self.config, key, None))))
        with open("config.py", "w") as fp:
            fp.write("".join(lines))

    def update_config(self, updates):
        updates = updates or {}
        unknown = []
        self._lock.acquire()
        try:
            for key in updates:
                if key not in CONFIG_FIELDS:
                    unknown.append(key)
            if unknown:
                raise ValueError("unknown config keys: %s" % ", ".join(unknown))
            if "API_IDLE_FACE" in updates and updates["API_IDLE_FACE"] not in GENERATED_FACES:
                raise ValueError("unknown face: %s" % updates["API_IDLE_FACE"])
            if "WIFI_MODE" in updates and updates["WIFI_MODE"] not in ("sta", "ap"):
                raise ValueError("WIFI_MODE must be 'sta' or 'ap'")
            for key, value in updates.items():
                setattr(self.config, key, value)
            self._apply_runtime_config()
            self._write_config_file()
        finally:
            self._lock.release()
        result = self.get_config()
        result["ok"] = True
        return result

    def get_faces(self):
        return list_faces()

    def _apply_face_locked(self, name, now_tuple=None, remember_face=True):
        if name not in GENERATED_FACES:
            raise ValueError("unknown face: %s" % name)
        if now_tuple is None:
            now_tuple = self._current_localtime()
        if remember_face:
            self.face = name
        self._display_face = name
        self._animation_frames = get_generated_frames(name)
        self._animation_index = 0
        if self._clock_window_active(now_tuple):
            self._clock_suppressed_minute = self._minute_key(now_tuple)
        self._clock_visible = False
        self._last_clock_second = None
        self.display.render_buffer(self._animation_frames[0])

    def set_face(self, name):
        self._lock.acquire()
        try:
            self._idle_active = False
            self._apply_face_locked(name)
        finally:
            self._lock.release()
        return {"ok": True, "face": self.face}

    def get_clock_settings(self):
        return {
            "enabled": self._clock_enabled,
            "visible": self._clock_visible,
            "timezone_offset_seconds": self._timezone_offset_seconds,
        }

    def set_clock_enabled(self, enabled):
        self._lock.acquire()
        try:
            self._clock_enabled = bool(enabled)
            if not self._clock_enabled:
                self._clock_visible = False
                self._last_clock_second = None
                if self._animation_frames:
                    self._animation_index = 0
                    self.display.render_buffer(self._animation_frames[self._animation_index])
        finally:
            self._lock.release()
        return {"ok": True, "clock": self.get_clock_settings()}

    def request_soft_reset(self):
        self._lock.acquire()
        try:
            self._soft_reset_requested = True
        finally:
            self._lock.release()
        return {"ok": True, "reloading": True}

    def mark_api_activity(self):
        self._lock.acquire()
        try:
            self._last_activity_ms = time.ticks_ms()
            if self._idle_active:
                self._idle_active = False
                self._apply_face_locked(self.face)
        finally:
            self._lock.release()

    def _enqueue_event(self, event_type, arguments=None):
        arguments = arguments or {}
        event_id = "evt-%d" % self._next_event_id
        self._next_event_id += 1
        event = {
            "id": event_id,
            "type": event_type,
            "arguments": arguments,
            "state": "queued",
            "result": None,
            "error": None,
        }
        self._event_queue.append(event_id)
        self._event_history[event_id] = event
        return event_id

    def submit_event(self, event_type, arguments=None):
        self._lock.acquire()
        try:
            event_id = self._enqueue_event(event_type, arguments)
            self._trim_event_history()
        finally:
            self._lock.release()
        return {
            "ok": True,
            "accepted": True,
            "event_id": event_id,
            "event": self.get_event_status(event_id),
        }

    def submit_events(self, events):
        events = events or []
        self._lock.acquire()
        try:
            event_ids = []
            queued_events = []
            for item in events:
                event_id = self._enqueue_event(item.get("type"), item.get("arguments", {}))
                event_ids.append(event_id)
                queued_events.append(dict(self._event_history[event_id]))
            self._trim_event_history()
        finally:
            self._lock.release()
        return {
            "ok": True,
            "accepted": True,
            "event_ids": event_ids,
            "events": queued_events,
        }

    def get_event_status(self, event_id):
        self._lock.acquire()
        try:
            event = self._event_history.get(event_id)
            if event is None:
                raise ValueError("unknown event: %s" % event_id)
            return dict(event)
        finally:
            self._lock.release()

    def _trim_event_history(self):
        if self._max_event_history <= 0:
            return
        while len(self._event_history) > self._max_event_history:
            oldest_id = None
            for event_id, event in self._event_history.items():
                if event["state"] in ("queued", "running"):
                    continue
                oldest_id = event_id
                break
            if oldest_id is None:
                return
            del self._event_history[oldest_id]

    def _execute_event(self, event_type, arguments):
        if event_type == "set_face":
            return self.set_face(arguments.get("name"))
        if event_type == "set_clock_enabled":
            return self.set_clock_enabled(arguments.get("enabled"))
        if event_type == "led_on":
            return self.led_on(
                arguments.get("r", 0),
                arguments.get("g", 0),
                arguments.get("b", 0),
                arguments.get("brightness", 1.0),
            )
        if event_type == "led_off":
            return self.led_off()
        if event_type == "reload_code":
            return self.request_soft_reset()
        raise ValueError("unknown event type: %s" % event_type)

    def process_next_event(self):
        self._lock.acquire()
        try:
            if not self._event_queue:
                return False
            event_id = self._event_queue.pop(0)
            event = self._event_history.get(event_id)
            if event is None:
                return False
            event["state"] = "running"
            event_type = event["type"]
            arguments = dict(event["arguments"])
        finally:
            self._lock.release()

        try:
            result = self._execute_event(event_type, arguments)
            state = "completed"
            error = None
        except Exception as exc:
            result = None
            state = "failed"
            error = str(exc)

        self._lock.acquire()
        try:
            event = self._event_history.get(event_id)
            if event is not None:
                event["state"] = state
                event["result"] = result
                event["error"] = error
                self._trim_event_history()
        finally:
            self._lock.release()
        return True

    def consume_soft_reset_request(self):
        self._lock.acquire()
        try:
            pending = self._soft_reset_requested
            self._soft_reset_requested = False
            return pending
        finally:
            self._lock.release()

    def perform_soft_reset(self):
        machine.soft_reset()

    def _current_localtime(self):
        now = time.time() + self._timezone_offset_seconds
        return time.localtime(now)

    def _minute_key(self, now_tuple):
        return (now_tuple[0], now_tuple[1], now_tuple[2], now_tuple[3], now_tuple[4])

    def _clock_window_active(self, now_tuple):
        if not self._clock_enabled or now_tuple[4] % 5 != 0:
            return False
        return self._clock_suppressed_minute != self._minute_key(now_tuple)

    def _render_clock(self, now_tuple):
        date_text = "%04d-%02d-%02d" % (now_tuple[0], now_tuple[1], now_tuple[2])
        time_text = "%02d:%02d:%02d" % (now_tuple[3], now_tuple[4], now_tuple[5])
        self.display.render_clock(date_text, time_text)

    def _check_idle_timeout(self):
        if self._idle_timeout_ms <= 0 or self._idle_active:
            return
        if time.ticks_diff(time.ticks_ms(), self._last_activity_ms) < self._idle_timeout_ms:
            return
        self._idle_active = True
        self._apply_face_locked(self._idle_face, remember_face=False)

    def tick(self):
        now_tuple = self._current_localtime()
        self._lock.acquire()
        try:
            self._check_idle_timeout()
        finally:
            self._lock.release()
        if self._clock_window_active(now_tuple):
            second = now_tuple[5]
            if (not self._clock_visible) or second != self._last_clock_second:
                self._lock.acquire()
                try:
                    self._render_clock(now_tuple)
                    self._clock_visible = True
                    self._last_clock_second = second
                finally:
                    self._lock.release()
            return False

        self._lock.acquire()
        try:
            if self._clock_suppressed_minute is not None and self._clock_suppressed_minute != self._minute_key(now_tuple):
                self._clock_suppressed_minute = None

            if self._clock_visible:
                self._clock_visible = False
                self._last_clock_second = None
                self._animation_index = 0
                if self._animation_frames:
                    self.display.render_buffer(self._animation_frames[0])

            frames = self._animation_frames
            if not frames:
                return False

            self.display.render_buffer(frames[self._animation_index])
            self._animation_index = (self._animation_index + 1) % len(frames)
            return True
        finally:
            self._lock.release()

    def run_animation_loop(self):
        while True:
            processed_event = self.process_next_event()
            animated = self.tick()
            self.led.tick()
            if self.consume_soft_reset_request():
                time.sleep_ms(100)
                self.perform_soft_reset()
            time.sleep_ms(self._animation_delay_ms if animated else (50 if processed_event else 200))

    def led_on(self, r, g, b, brightness=1.0):
        return {"ok": True, "led": self.led.on(r, g, b, brightness)}

    def led_off(self):
        return {"ok": True, "led": self.led.off()}
