from machine import Pin, I2C
from lib.ssd1306 import SSD1306_I2C
from buddy.faces import draw_face


class Display:
    def __init__(self, config):
        self.config = config
        self.width = config.OLED_WIDTH
        self.height = config.OLED_HEIGHT
        self.i2c = I2C(
            config.I2C_ID,
            scl=Pin(config.I2C_SCL_PIN),
            sda=Pin(config.I2C_SDA_PIN),
            freq=400000,
        )
        self.oled = SSD1306_I2C(
            config.OLED_WIDTH,
            config.OLED_HEIGHT,
            self.i2c,
            addr=config.OLED_ADDR,
        )

    def scan(self):
        return self.i2c.scan()

    def fill(self, color):
        self.oled.fill(color)

    def pixel(self, x, y, color):
        self.oled.pixel(x, y, color)

    def hline(self, x, y, w, color):
        self.oled.hline(x, y, w, color)

    def vline(self, x, y, h, color):
        self.oled.vline(x, y, h, color)

    def line(self, x0, y0, x1, y1, color):
        self.oled.line(x0, y0, x1, y1, color)

    def fill_rect(self, x, y, w, h, color):
        self.oled.fill_rect(x, y, w, h, color)

    def text(self, text, x, y, color=1):
        self.oled.text(text, x, y, color)

    def show(self):
        self.oled.show()

    def text_centered(self, text, y, color=1):
        x = max(0, (self.width - len(text) * 8) // 2)
        self.text(text, x, y, color)

    def render_clock(self, date_text, time_text):
        self.fill(0)
        self.text_centered(time_text, 20)
        self.text_centered(date_text, 36)
        self.show()

    def render_connecting(self):
        self.fill(0)
        self.text_centered("connecting", 28)
        self.show()

    def render_boot_info(self, title, line1_label, line1_text, line2_label, line2_text):
        self.fill(0)
        self.text_centered(title[:16], 0)
        self.text((line1_label or "")[:5], 0, 18)
        self.text((line1_text or "")[:16], 0, 28)
        self.text((line2_label or "")[:5], 0, 42)
        self.text((line2_text or "")[:16], 0, 52)
        self.show()

    def render_ap_boot_info(self, title, ssid, password, ip_text):
        self.fill(0)
        self.text_centered(title[:16], 0)
        self.text((ssid or "")[:16], 0, 16)
        self.text((password or "")[:16], 0, 32)
        self.text((ip_text or "")[:16], 0, 48)
        self.show()

    def round_rect(self, x, y, w, h, r, color):
        self.hline(x + r, y, w - 2 * r, color)
        self.hline(x + r, y + h - 1, w - 2 * r, color)
        self.vline(x, y + r, h - 2 * r, color)
        self.vline(x + w - 1, y + r, h - 2 * r, color)
        self.pixel(x + 1, y + 1, color)
        self.pixel(x + w - 2, y + 1, color)
        self.pixel(x + 1, y + h - 2, color)
        self.pixel(x + w - 2, y + h - 2, color)
        self.hline(x + 2, y, r - 1, color)
        self.hline(x + w - r - 1, y, r - 1, color)
        self.hline(x + 2, y + h - 1, r - 1, color)
        self.hline(x + w - r - 1, y + h - 1, r - 1, color)

    def fill_round_rect(self, x, y, w, h, r, color):
        self.fill_rect(x + r, y, w - 2 * r, h, color)
        self.fill_rect(x, y + r, w, h - 2 * r, color)
        self.fill_rect(x + 1, y + 1, r, r, color)
        self.fill_rect(x + w - r - 1, y + 1, r, r, color)
        self.fill_rect(x + 1, y + h - r - 1, r, r, color)
        self.fill_rect(x + w - r - 1, y + h - r - 1, r, r, color)

    def arc_smile(self, x, y, w, h):
        self.line(x + 2, y + 4, x + 8, y + h - 1, 1)
        self.hline(x + 8, y + h - 1, w - 16, 1)
        self.line(x + w - 9, y + h - 1, x + w - 3, y + 4, 1)

    def arc_frown(self, x, y, w, h):
        self.line(x + 2, y + h - 1, x + 8, y + 2, 1)
        self.hline(x + 8, y + 2, w - 16, 1)
        self.line(x + w - 9, y + 2, x + w - 3, y + h - 1, 1)

    def render_buffer(self, frame_bytes):
        self.oled.buffer[:] = frame_bytes
        self.oled.show()

    def render_face(self, name):
        draw_face(self, name)


class NullDisplay:
    def __init__(self, reason="display unavailable"):
        self.reason = reason
        self.width = 128
        self.height = 64

    def scan(self):
        return []

    def render_face(self, name):
        return None

    def render_clock(self, date_text, time_text):
        return None

    def render_connecting(self):
        return None

    def render_boot_info(self, title, line1_label, line1_text, line2_label, line2_text):
        return None

    def render_ap_boot_info(self, title, ssid, password, ip_text):
        return None
