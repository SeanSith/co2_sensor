# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A CircuitPython firmware project for the **Unexpected Maker FeatherS3** (ESP32S3), which reads CO2, temperature, and humidity from an **Adafruit SCD4X** sensor and publishes the data via MQTT. The board runs **CircuitPython 9.2.9**.

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

## Monitoring & Observability

A Prometheus collector is exposed at `http://prometheus.smithpeople.org` (LAN access only — not reachable from the public internet). It scrapes the MQTT-published metrics from this sensor. Use it to correlate readings over time when debugging stuck-data or drift issues.

## Task Management

When completing any work that addresses an item in `TODO.md`, remove that item from the file before committing. Do not leave resolved items in place.

## Known Issues

See `TODO.md` for the full list. The two active problems:

1. **Memory leak** — free memory trends downward over long runtimes. Root cause is function objects (`connect`/`disconnect` callbacks) being allocated inside the `while True` loop, plus incomplete cleanup of `pool` and `mqtt_client` on failure paths.

2. **Sensor gets stuck** — the SCD4X's Automatic Self-Calibration (ASC) assumes weekly exposure to ~400 ppm outdoor air. Running permanently indoors causes it to drift and eventually report a fixed value. Disabling ASC (`scd4x.self_calibration_enabled = False`) is the intended fix for an always-indoor deployment.

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

| Color | Meaning |
|-------|---------|
| Green | WiFi + MQTT connected successfully |
| Red | Any failure (WiFi, MQTT connect, sensor read, or publish) |
| Off | Sleeping between readings |

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

To update libraries, download the matching bundle for CircuitPython 9.x from [circuitpython.org/libraries](https://circuitpython.org/libraries).
