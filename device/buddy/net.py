import network
import time


def connect_wifi(config):
    mode = getattr(config, "WIFI_MODE", "sta")
    if mode == "ap":
        ap = network.WLAN(network.AP_IF)
        ap.active(True)
        ssid = getattr(config, "AP_SSID", "AIHarnessDesktopBuddy")
        password = getattr(config, "AP_PASSWORD", "buddybuddy")
        if password:
            ap.config(essid=ssid, password=password)
        else:
            ap.config(essid=ssid)
        while not ap.active():
            time.sleep_ms(100)
        return {"mode": "ap", "ip": ap.ifconfig()[0], "ssid": ssid}

    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    if not sta.isconnected():
        sta.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        for _ in range(200):
            if sta.isconnected():
                break
            time.sleep_ms(100)
    if not sta.isconnected():
        raise RuntimeError("wifi connection failed")
    return {"mode": "sta", "ip": sta.ifconfig()[0], "ssid": config.WIFI_SSID}
