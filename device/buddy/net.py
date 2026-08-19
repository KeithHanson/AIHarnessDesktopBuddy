import machine
import network
import socket
import struct
import time

try:
    import ntptime
except ImportError:
    ntptime = None


NTP_DELTA = 2208988800


def _set_rtc_from_unix(unix_time):
    tm = time.gmtime(unix_time)
    machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], tm[5], 0))


def _sync_time_via_socket(host):
    addr = socket.getaddrinfo(host, 123)[0][-1]
    payload = bytearray(48)
    payload[0] = 0x1B
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.settimeout(2)
        sock.sendto(payload, addr)
        msg = sock.recv(48)
    finally:
        sock.close()
    if len(msg) < 48:
        raise OSError("short NTP response")
    seconds = struct.unpack("!I", msg[40:44])[0]
    _set_rtc_from_unix(seconds - NTP_DELTA)


def sync_time(config):
    host = getattr(config, "NTP_HOST", None) or "pool.ntp.org"
    methods = []
    if ntptime is not None:
        methods.append("ntptime")
    methods.append("socket")
    last_error = None
    attempts = 0
    for method in methods:
        for _ in range(3):
            attempts += 1
            try:
                if method == "ntptime":
                    ntptime.host = host
                    ntptime.settime()
                else:
                    _sync_time_via_socket(host)
                return {
                    "ok": True,
                    "host": host,
                    "method": method,
                    "attempts": attempts,
                    "error": None,
                }
            except Exception as exc:
                last_error = "%s: %s" % (method, exc)
                time.sleep_ms(200)
    return {
        "ok": False,
        "host": host,
        "method": None,
        "attempts": attempts,
        "error": last_error or "NTP sync failed",
    }


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
        "time_sync": {
            "ok": False,
            "host": getattr(config, "NTP_HOST", None) or "pool.ntp.org",
            "method": None,
            "attempts": 0,
            "error": "AP mode; NTP not attempted",
        },
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
    time_sync = sync_time(config)
    return {
        "mode": "sta",
        "ip": sta.ifconfig()[0],
        "ssid": config.WIFI_SSID,
        "password": None,
        "time_synced": bool(time_sync.get("ok")),
        "time_sync": time_sync,
    }
