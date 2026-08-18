import neopixel
import time
from machine import Pin


class StatusLed:
    def __init__(self, config):
        self.np = neopixel.NeoPixel(Pin(config.LED_PIN), config.LED_COUNT)
        self.color_order = getattr(config, "LED_COLOR_ORDER", "GRB").upper()
        self.pulse_period_ms = int(getattr(config, "LED_PULSE_PERIOD_MS", 3000))
        self.pulse_hold_off_ms = int(getattr(config, "LED_PULSE_HOLD_OFF_MS", 1000))
        self.state = {"on": False, "r": 0, "g": 0, "b": 0, "brightness": 0.0}
        self._pulse_start_ms = time.ticks_ms()
        self.off()

    def _ordered(self, r, g, b):
        values = {"R": r, "G": g, "B": b}
        return tuple(values[c] for c in self.color_order)

    def _write(self, r, g, b, brightness):
        brightness = max(0.0, min(1.0, float(brightness)))
        rr = int(max(0, min(255, r)) * brightness)
        gg = int(max(0, min(255, g)) * brightness)
        bb = int(max(0, min(255, b)) * brightness)
        self.np[0] = self._ordered(rr, gg, bb)
        self.np.write()

    def _pulse_brightness(self):
        if not self.state["on"]:
            return 0.0
        period = max(400, self.pulse_period_ms)
        hold = max(0, self.pulse_hold_off_ms)
        ramp_total = max(200, period - hold)
        elapsed = time.ticks_diff(time.ticks_ms(), self._pulse_start_ms) % period
        if elapsed < hold:
            return 0.0
        ramp_elapsed = elapsed - hold
        half = ramp_total / 2.0
        if ramp_elapsed < half:
            wave = ramp_elapsed / half
        else:
            wave = max(0.0, 1.0 - ((ramp_elapsed - half) / half))
        return self.state["brightness"] * wave

    def tick(self):
        if not self.state["on"]:
            return False
        self._write(self.state["r"], self.state["g"], self.state["b"], self._pulse_brightness())
        return True

    def on(self, r, g, b, brightness=1.0):
        self.state = {
            "on": True,
            "r": int(r),
            "g": int(g),
            "b": int(b),
            "brightness": float(brightness),
        }
        self._pulse_start_ms = time.ticks_ms()
        self.tick()
        return self.state

    def off(self):
        self.np[0] = (0, 0, 0)
        self.np.write()
        self.state = {"on": False, "r": 0, "g": 0, "b": 0, "brightness": 0.0}
        return self.state
