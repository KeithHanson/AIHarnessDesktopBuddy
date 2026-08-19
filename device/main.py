import _thread
import time
import config
from buddy.display import Display, NullDisplay
from buddy.led import StatusLed
from buddy.net import connect_wifi
from buddy.server import BuddyServer
from buddy.state import BuddyState


def main():
    try:
        display = Display(config)
        print("i2c scan:", display.scan())
        display.render_connecting()
    except Exception as exc:
        print("display init failed:", exc)
        display = NullDisplay(str(exc))

    print("startup delay: 5s before network init")
    time.sleep(5)

    net = connect_wifi(config)
    print("network:", net)

    led = StatusLed(config)
    state = BuddyState(display, led, config)
    state.set_boot_info(net)

    server = BuddyServer(
        state=state,
        device_name=getattr(config, "DEVICE_NAME", "AIHarnessDesktopBuddy"),
        bind_ip="0.0.0.0",
        port=getattr(config, "HTTP_PORT", 80),
    )
    _thread.start_new_thread(server.serve_forever, ())
    state.run_animation_loop()


main()
