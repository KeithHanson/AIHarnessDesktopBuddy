import _thread
import time
from buddy.faces import list_faces, get_generated_frames
from buddy.generated_faces import GENERATED_FACES


class BuddyState:
    def __init__(self, display, led):
        self.display = display
        self.led = led
        self.face = "neutral"
        self._lock = _thread.allocate_lock()
        self._animation_frames = None
        self._animation_index = 0
        self._animation_delay_ms = 120
        self.set_face(self.face)

    def get_state(self):
        return {
            "face": self.face,
            "led": self.led.state,
        }

    def get_faces(self):
        return list_faces()

    def set_face(self, name):
        if name not in GENERATED_FACES:
            raise ValueError("unknown face: %s" % name)
        self._lock.acquire()
        try:
            self.face = name
            self._animation_frames = get_generated_frames(name)
            self._animation_index = 0
            self.display.render_buffer(self._animation_frames[0])
        finally:
            self._lock.release()
        return {"ok": True, "face": self.face}

    def tick(self):
        self._lock.acquire()
        try:
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
            animated = self.tick()
            time.sleep_ms(self._animation_delay_ms if animated else 100)

    def led_on(self, r, g, b, brightness=1.0):
        return {"ok": True, "led": self.led.on(r, g, b, brightness)}

    def led_off(self):
        return {"ok": True, "led": self.led.off()}
