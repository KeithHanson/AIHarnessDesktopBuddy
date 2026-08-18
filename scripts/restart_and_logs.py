#!/usr/bin/env python3
import sys
import time
import serial

port = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"
ser = serial.Serial(port, 115200, timeout=0.2)
try:
    ser.write(b"\r\x03\x03")
    time.sleep(0.2)
    ser.reset_input_buffer()
    ser.write(b"\x04")  # Ctrl-D soft reboot
    end = time.time() + 6
    out = bytearray()
    while time.time() < end:
        chunk = ser.read(ser.in_waiting or 1)
        if chunk:
            out.extend(chunk)
    sys.stdout.write(out.decode("utf-8", "replace"))
finally:
    ser.close()
