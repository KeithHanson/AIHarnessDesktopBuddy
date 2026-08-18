import neopixel
from machine import Pin


class StatusLed:
    def __init__(self, config):
        self.np = neopixel.NeoPixel(Pin(config.LED_PIN), config.LED_COUNT)
        self.color_order = getattr(config, "LED_COLOR_ORDER", "GRB").upper()
        self.state = {"on": False, "r": 0, "g": 0, "b": 0, "brightness": 0.0}
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

    def on(self, r, g, b, brightness=1.0):
        self._write(r, g, b, brightness)
        self.state = {
            "on": True,
            "r": int(r),
            "g": int(g),
            "b": int(b),
            "brightness": float(brightness),
        }
        return self.state

    def off(self):
        self.np[0] = (0, 0, 0)
        self.np.write()
        self.state = {"on": False, "r": 0, "g": 0, "b": 0, "brightness": 0.0}
        return self.state
