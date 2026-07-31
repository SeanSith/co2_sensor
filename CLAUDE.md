# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A CircuitPython firmware project for the **Unexpected Maker FeatherS3** (ESP32S3), which reads CO2, temperature, and humidity from an **Adafruit SCD4X** sensor and publishes the data via MQTT. The board runs **CircuitPython 10.x** — check `CIRCUITPY/boot_out.txt` for the exact version currently installed.

There is no build step. CircuitPython executes `code.py` directly from the device's flash filesystem.

## Deployment

Use the deploy script — do not use `cp` directly:

```bash
./tools/deploy.sh
```

Copies `code.py` and `feathers3.py` to `/Volumes/CIRCUITPY/`. The device resets and reruns `code.py` automatically.

## Monitoring

Use the monitor script — do not use `screen` or invoke via `python3`:

```bash
./tools/monitor.py                   # run until Ctrl-C
./tools/monitor.py --duration 90     # run for 90 seconds
```

Streams serial output to stdout and `/tmp/circuitpy.log`.

## Configuration

All runtime configuration lives in `settings.toml` (gitignored, never committed):

| Key | Purpose |
|-----|---------|
| `SENSOR_NAME` | Device identity; used as WiFi hostname and in MQTT topic |
| `WIFI_SSID` / `WIFI_PASSWORD` | Network credentials |
| `MQTT_BROKER` / `MQTT_PORT` / `MQTT_USERNAME` / `MQTT_PASSWORD` | MQTT broker connection |
| `PUSH_INTERVAL` | Seconds between readings (default: 60) |
| `ALTITUDE` | Meters above sea level, used to calibrate the SCD4X |

A template `settings.toml` must be created manually on each new device.

ASC (Automatic Self-Calibration) is disabled every boot in `code.py` — see README.md § Sensor Calibration for why an always-indoor SCD4X needs this.

## Monitoring & Observability

A Prometheus collector is exposed at `http://prometheus.smithpeople.org` (LAN access only — not reachable from the public internet). It scrapes the MQTT-published metrics from this sensor. Use it to correlate readings over time when debugging stuck-data or drift issues.

## Upgrading Firmware & Libraries

Check the installed version via `CIRCUITPY/boot_out.txt` and compare against the latest stable release for `unexpectedmaker_feathers3` at [circuitpython.org](https://circuitpython.org/board/unexpectedmaker_feathers3/). CircuitPython only ships point releases within the current major version, so "latest" may mean a major-version jump (e.g. 9.x → 10.x) — check that release's changelog on the `adafruit/circuitpython` GitHub releases page for breaking changes before jumping.

### Flashing new firmware

Prefer `esptool` over the UF2 drag-and-drop dance:

```bash
pip3 install --user esptool
python3 -m esptool --port /dev/cu.usbmodem* flash-id                     # confirms flash size
python3 -m esptool --port /dev/cu.usbmodem* write-flash 0x0 <firmware>.bin
```

The FeatherS3's native USB-Serial/JTAG interface lets esptool auto-reset into the ROM bootloader with **zero button presses** — far more reliable than the manual double-tap/BOOT+RESET gestures.

Pitfalls hit in practice:
- **Don't press RESET manually right after an esptool flash.** esptool already triggers its own reset; a manual press soon after can read as TinyUF2's "double-reset" gesture and drop the board into its UF2 bootloader (a drive like `UFTHRS3BOOT` appears) instead of booting the new firmware.
- **If that happens, it's not stuck** — copy the same `.uf2` file onto that bootloader drive. The board reboots the instant it finishes receiving the payload, so `cp` reporting an I/O error mid-copy is expected, not a failure.
- **Major-version bumps on ESP32-S2/S3 boards with 4MB flash** need a TinyUF2 bootloader update (≥0.33.0) first, or the UF2 load silently fails. This board has 16MB flash (confirm via `flash-id` or the bootloader drive's `INFO_UF2.TXT`), so that requirement doesn't apply here — but check flash size before a major bump on any board.
- Shell commands may run sandboxed and not see freshly mounted volumes or full USB device info — `system_profiler`/`ioreg` can return empty even when the Mac sees the device fine. If a flash looks stuck, confirm the actual state in Finder rather than trusting shell inspection.
- Back up `settings.toml`, `code.py`, and `feathers3.py` off the device before flashing. The user filesystem partition should survive a firmware flash, but it's cheap insurance.

### Updating libraries

`.mpy` bytecode is tied to the CircuitPython **major** version — grab the bundle build matching the new major version specifically (the [bundle release](https://github.com/adafruit/Adafruit_CircuitPython_Bundle/releases/latest) ships `9.x` and `10.x` builds side by side), not just whatever's newest. After swapping `CIRCUITPY/lib/`, mirror the same files into the repo's local (gitignored) `lib/` so the dev environment matches.

### After any upgrade

Redeploy via `./tools/deploy.sh`, then watch `./tools/monitor.py` through at least one full sensor cycle before calling it done.

## Task Management

When completing any work that addresses an item in `TODO.md`, remove that item from the file before committing. Do not leave resolved items in place.

## Known Issues

See `TODO.md` for planned work. One active problem:

- **Memory leak** — free memory still trends downward slowly over long runtimes (confirmed via the Prometheus collector). Commit `a641a46` (hoisting `connect`/`disconnect` callbacks to module level, guaranteeing `pool`/`mqtt_client` cleanup in `finally`) reduced but did not eliminate it — root cause is still unidentified.

## Architecture

### Main loop (`code.py`)

Each iteration of the `while True` loop:

1. **Enable WiFi** → connect using `WIFI_SSID`/`WIFI_PASSWORD`
2. **Connect MQTT** → broker at `MQTT_BROKER:MQTT_PORT`
3. **Single-shot sensor read** → `scd4x.measure_single_shot()` (not continuous mode, to save power)
4. **Build JSON payload** → CO2 (ppm), temperature (°C), humidity (%), battery voltage (V), charging (0/1), free memory (bytes), uptime (seconds)
5. **Publish** to topic `sensors/environmental/{SENSOR_NAME}`
6. **Disconnect MQTT** → `mqtt_client.deinit()`
7. **Disable WiFi radio** → `wifi.radio.enabled = False` (power saving)
8. **`gc.collect()`** → explicit garbage collection (mitigates a known memory leak)
9. **Sleep** `PUSH_INTERVAL` seconds

### NeoPixel status LED

See README.md § Status LED for the color meanings table.

### Board helper (`feathers3.py`)

Provides hardware abstractions for the FeatherS3 board:
- `get_battery_voltage()` — reads the battery ADC via a voltage divider (R1=337kΩ, R2=160kΩ)
- `get_vbus_present()` — detects if USB 5V is present (i.e., charging)
- LED and LDO2 power rail control

### Libraries (`lib/`)

Pre-compiled `.mpy` files installed from the Adafruit CircuitPython bundle. Gitignored — must be installed manually on each device. Listed in `requirements.txt`:
- `adafruit_minimqtt` — MQTT client
- `adafruit_scd4x` — SCD40/SCD41 CO2 sensor driver
- `neopixel` — NeoPixel control

See § Upgrading Firmware & Libraries above for how to update these.
