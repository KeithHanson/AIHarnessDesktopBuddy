import network
import time

try:
    import ntptime
except ImportError:
    ntptime = None


def sync_time(config):
    if ntptime is None:
        return False
    host = getattr(config, "NTP_HOST", None)
    if host:
        ntptime.host = host
    for _ in range(3):
        try:
            ntptime.settime()
            return True
        except Exception:
            time.sleep_ms(200)
    return False


def _start_ap(config):
    sta = network.WLAN(network.STA_IF)
    if sta.active():
        try:
            if sta.isconnected():
                sta.disconnect()
        except Exception:
            pass
        sta.active(False)

    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ssid = getattr(config, "AP_SSID", "AIHarnessDesktopBuddy")
    password = getattr(config, "AP_PASSWORD", "buddybuddy")
    if password:
        authmode = getattr(network, "AUTH_WPA_WPA2_PSK", None)
        if authmode is None:
            authmode = getattr(network, "AUTH_WPA2_PSK", None)
        if authmode is not None:
            ap.config(essid=ssid, password=password, authmode=authmode)
        else:
            ap.config(essid=ssid, password=password)
    else:
        ap.config(essid=ssid)
    while not ap.active():
        time.sleep_ms(100)
    return {
        "mode": "ap",
        "ip": ap.ifconfig()[0],
        "ssid": ssid,
        "password": password,
        "time_synced": False,
    }


def connect_wifi(config):
    mode = getattr(config, "WIFI_MODE", "sta")
    if mode == "ap":
        return _start_ap(config)

    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    if not sta.isconnected():
        security = getattr(config, "WIFI_SECURITY", "wpa2")
        if security == "open" or not getattr(config, "WIFI_PASSWORD", ""):
            sta.connect(config.WIFI_SSID)
        else:
            sta.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        for _ in range(200):
            if sta.isconnected():
                break
            time.sleep_ms(100)
    if not sta.isconnected():
        return _start_ap(config)
    return {
        "mode": "sta",
        "ip": sta.ifconfig()[0],
        "ssid": config.WIFI_SSID,
        "password": None,
        "time_synced": sync_time(config),
    }
