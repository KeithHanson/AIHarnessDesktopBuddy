import _thread
import config
from buddy.display import Display, NullDisplay
from buddy.led import StatusLed
from buddy.net import connect_wifi
from buddy.server import BuddyServer
from buddy.state import BuddyState


def main():
    net = connect_wifi(config)
    print("network:", net)

    try:
        display = Display(config)
        print("i2c scan:", display.scan())
    except Exception as exc:
        print("display init failed:", exc)
        display = NullDisplay(str(exc))

    led = StatusLed(config)
    state = BuddyState(display, led)

    server = BuddyServer(
        state=state,
        device_name=getattr(config, "DEVICE_NAME", "AIHarnessDesktopBuddy"),
        bind_ip="0.0.0.0",
        port=getattr(config, "HTTP_PORT", 8080),
    )
    _thread.start_new_thread(server.serve_forever, ())
    state.run_animation_loop()


main()
