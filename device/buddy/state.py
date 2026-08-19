import _thread
import time
import machine
from buddy.faces import list_faces, get_generated_frames
from buddy.generated_faces import GENERATED_FACES
from buddy.net import sync_time


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
    "WIFI_SECURITY",
    "AP_SSID",
    "AP_PASSWORD",
    "CLOCK_OVERLAY_ENABLED",
    "CLOCK_OVERLAY_INTERVAL_MINUTES",
    "CLOCK_OVERLAY_DURATION_SECONDS",
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
        self._manual_clock_deadline_ms = None
        self._clock_enabled = bool(
            getattr(config, "CLOCK_OVERLAY_ENABLED", True)
            if config is not None
            else True
        )
        self._clock_interval_minutes = int(
            getattr(config, "CLOCK_OVERLAY_INTERVAL_MINUTES", 5)
            if config is not None
            else 5
        )
        self._clock_duration_seconds = int(
            getattr(config, "CLOCK_OVERLAY_DURATION_SECONDS", 60)
            if config is not None
            else 60
        )
        self._timezone_offset_seconds = int(
            getattr(config, "TIMEZONE_OFFSET_SECONDS", 0)
            if config is not None
            else 0
        )
        self._soft_reset_requested = False
        self._time_sync = {"ok": False, "host": getattr(config, "NTP_HOST", None), "method": None, "attempts": 0, "error": "not yet synced"}
        self._boot_info = None
        self._boot_info_active = False
        self._boot_info_rendered = False
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
        self._lock.acquire()
        try:
            self._apply_face_locked(self.face)
        finally:
            self._lock.release()

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
            "boot_info": {
                "active": self._boot_info_active,
                "mode": None if self._boot_info is None else self._boot_info.get("mode"),
                "network": None if self._boot_info is None else self._boot_info.get("ssid"),
                "ip": None if self._boot_info is None else self._boot_info.get("ip"),
            },
            "time_sync": dict(self._time_sync),
            "events": {
                "queued": len(self._event_queue),
                "history": len(self._event_history),
            },
        }

    def _apply_runtime_config(self):
        config = self.config
        self._clock_enabled = bool(getattr(config, "CLOCK_OVERLAY_ENABLED", True))
        self._clock_interval_minutes = int(getattr(config, "CLOCK_OVERLAY_INTERVAL_MINUTES", 5))
        self._clock_duration_seconds = int(getattr(config, "CLOCK_OVERLAY_DURATION_SECONDS", 60))
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
                    "WIFI_SECURITY",
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
            if "WIFI_SECURITY" in updates and updates["WIFI_SECURITY"] not in ("open", "wpa2", "wpa_wpa2"):
                raise ValueError("WIFI_SECURITY must be 'open', 'wpa2', or 'wpa_wpa2'")
            self._validate_clock_settings(
                enabled=updates.get("CLOCK_OVERLAY_ENABLED"),
                interval_minutes=updates.get("CLOCK_OVERLAY_INTERVAL_MINUTES"),
                duration_seconds=updates.get("CLOCK_OVERLAY_DURATION_SECONDS"),
            )
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

    def set_boot_info(self, net):
        self._lock.acquire()
        try:
            self._boot_info = {
                "mode": net.get("mode"),
                "ssid": net.get("ssid"),
                "ip": net.get("ip"),
                "password": net.get("password"),
            }
            self._time_sync = dict(net.get("time_sync") or {"ok": False, "host": getattr(self.config, "NTP_HOST", None), "method": None, "attempts": 0, "error": "not attempted"})
            self._boot_info_active = True
            self._boot_info_rendered = False
            if net.get("mode") == "sta" and net.get("ip"):
                self.led.on(0, 255, 0, 0.3)
            else:
                self.led.off()
        finally:
            self._lock.release()

    def _render_boot_info_locked(self):
        if not self._boot_info:
            return
        mode = (self._boot_info.get("mode") or "").upper()
        title = "WiFi %s" % mode
        if self._boot_info.get("mode") == "ap":
            self.display.render_ap_boot_info(
                title[:16],
                "AP: %s" % (self._boot_info.get("ssid") or ""),
                "PW: %s" % (self._boot_info.get("password") or ""),
                "IP: %s" % (self._boot_info.get("ip") or ""),
            )
        else:
            self.display.render_boot_info(
                title[:16],
                "NET:",
                self._boot_info.get("ssid") or "",
                "IP:",
                self._boot_info.get("ip") or "",
            )
        self._boot_info_rendered = True

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
            self._boot_info_active = False
            self._apply_face_locked(name)
        finally:
            self._lock.release()
        return {"ok": True, "face": self.face}

    def get_clock_settings(self):
        return {
            "enabled": self._clock_enabled,
            "visible": self._clock_visible,
            "manual_active": self._manual_clock_active(),
            "interval_minutes": self._clock_interval_minutes,
            "duration_seconds": self._clock_duration_seconds,
            "timezone_offset_seconds": self._timezone_offset_seconds,
            "time_sync": dict(self._time_sync),
        }

    def _validate_manual_clock_duration(self, duration_seconds=None):
        if duration_seconds is None:
            return self._clock_duration_seconds
        duration_seconds = int(duration_seconds)
        if duration_seconds < 1:
            raise ValueError("duration_seconds must be >= 1")
        return duration_seconds

    def _validate_clock_settings(self, enabled=None, interval_minutes=None, duration_seconds=None):
        if enabled is not None and not isinstance(enabled, bool):
            raise ValueError("enabled must be true or false")
        if interval_minutes is not None:
            interval_minutes = int(interval_minutes)
            if interval_minutes < 1:
                raise ValueError("CLOCK_OVERLAY_INTERVAL_MINUTES must be >= 1")
        if duration_seconds is not None:
            duration_seconds = int(duration_seconds)
            if duration_seconds < 1:
                raise ValueError("CLOCK_OVERLAY_DURATION_SECONDS must be >= 1")
        if interval_minutes is None:
            interval_minutes = self._clock_interval_minutes
        if duration_seconds is None:
            duration_seconds = self._clock_duration_seconds
        if duration_seconds > interval_minutes * 60:
            raise ValueError("CLOCK_OVERLAY_DURATION_SECONDS must be <= CLOCK_OVERLAY_INTERVAL_MINUTES * 60")
        return interval_minutes, duration_seconds

    def update_clock_settings(self, enabled=None, interval_minutes=None, duration_seconds=None, persist=False):
        interval_minutes, duration_seconds = self._validate_clock_settings(enabled, interval_minutes, duration_seconds)
        self._lock.acquire()
        try:
            if enabled is not None:
                self._clock_enabled = enabled
                if self.config is not None:
                    setattr(self.config, "CLOCK_OVERLAY_ENABLED", enabled)
            self._clock_interval_minutes = interval_minutes
            self._clock_duration_seconds = duration_seconds
            if self.config is not None:
                setattr(self.config, "CLOCK_OVERLAY_INTERVAL_MINUTES", interval_minutes)
                setattr(self.config, "CLOCK_OVERLAY_DURATION_SECONDS", duration_seconds)
            self._clock_suppressed_minute = None
            if not self._clock_enabled:
                self._clock_visible = False
                self._last_clock_second = None
                if self._animation_frames:
                    self._animation_index = 0
                    self.display.render_buffer(self._animation_frames[self._animation_index])
            if persist:
                self._write_config_file()
        finally:
            self._lock.release()
        return {"ok": True, "clock": self.get_clock_settings()}

    def set_clock_enabled(self, enabled):
        return self.update_clock_settings(enabled=enabled, persist=True)

    def _manual_clock_active(self):
        deadline = self._manual_clock_deadline_ms
        if deadline is None:
            return False
        return time.ticks_diff(deadline, time.ticks_ms()) > 0

    def show_clock_now(self, duration_seconds=None):
        duration_seconds = self._validate_manual_clock_duration(duration_seconds)
        now_tuple = self._current_localtime()
        self._lock.acquire()
        try:
            self._boot_info_active = False
            self._manual_clock_deadline_ms = time.ticks_add(time.ticks_ms(), duration_seconds * 1000)
            self._render_clock(now_tuple)
            self._clock_visible = True
            self._last_clock_second = now_tuple[5]
        finally:
            self._lock.release()
        return {"ok": True, "clock": self.get_clock_settings()}

    def sync_time_now(self):
        result = sync_time(self.config)
        self._lock.acquire()
        try:
            self._time_sync = dict(result)
        finally:
            self._lock.release()
        return {"ok": bool(result.get("ok")), "time_sync": dict(result), "clock": self.get_clock_settings()}

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
        if event_type == "show_clock_now":
            return self.show_clock_now(arguments.get("duration_seconds"))
        if event_type == "sync_time":
            return self.sync_time_now()
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
        if not self._clock_enabled:
            return False
        if now_tuple[4] % self._clock_interval_minutes != 0:
            return False
        if now_tuple[5] >= self._clock_duration_seconds:
            return False
        return self._clock_suppressed_minute != self._minute_key(now_tuple)

    def _render_active_clock(self, now_tuple):
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
            if self._boot_info_active:
                if not self._boot_info_rendered:
                    self._render_boot_info_locked()
                return False
        finally:
            self._lock.release()
        if self._manual_clock_active():
            return self._render_active_clock(now_tuple)

        if self._clock_window_active(now_tuple):
            return self._render_active_clock(now_tuple)

        self._lock.acquire()
        try:
            if self._clock_suppressed_minute is not None and self._clock_suppressed_minute != self._minute_key(now_tuple):
                self._clock_suppressed_minute = None
            if not self._manual_clock_active():
                self._manual_clock_deadline_ms = None

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
