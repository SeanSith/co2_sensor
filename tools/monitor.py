#!/usr/bin/env python3
"""
Stream CircuitPython serial output to stdout and /tmp/circuitpy.log.

Uses os.open + os.read for unbuffered direct reads from the serial port.

Usage:
    python3 tools/monitor.py [port] [--duration SECONDS]

    port defaults to first /dev/cu.usbmodem* found.
    duration defaults to unlimited (Ctrl-C to stop).
"""

import errno
import glob
import os
import subprocess
import sys
import time

LOG_PATH = "/tmp/circuitpy.log"


def find_port():
    matches = sorted(glob.glob("/dev/cu.usbmodem*"))
    if not matches:
        print("No device found. Connect the FeatherS3 and retry.", file=sys.stderr)
        sys.exit(1)
    return matches[0]


def main():
    port = None
    duration = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--duration" and i + 1 < len(args):
            duration = float(args[i + 1])
            i += 2
        elif not args[i].startswith("--"):
            port = args[i]
            i += 1
        else:
            i += 1

    if port is None:
        port = find_port()

    subprocess.run(
        ["stty", "-f", port, "115200", "raw", "-echo"],
        check=True,
        capture_output=True,
    )

    print(f"Monitoring {port} → {LOG_PATH}", file=sys.stderr)
    print("Press Ctrl-C to stop.", file=sys.stderr)

    deadline = time.monotonic() + duration if duration else None

    fd = os.open(port, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        with open(LOG_PATH, "wb") as log:
            while True:
                if deadline and time.monotonic() >= deadline:
                    break
                try:
                    chunk = os.read(fd, 256)
                    if chunk:
                        sys.stdout.buffer.write(chunk)
                        sys.stdout.buffer.flush()
                        log.write(chunk)
                        log.flush()
                except OSError as e:
                    if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                        time.sleep(0.05)
                    else:
                        raise
    except KeyboardInterrupt:
        pass
    finally:
        os.close(fd)

    print(f"\nLog saved to {LOG_PATH} ({os.path.getsize(LOG_PATH)} bytes)", file=sys.stderr)


if __name__ == "__main__":
    main()
