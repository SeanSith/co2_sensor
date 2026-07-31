# CO2 Sensor

CircuitPython firmware for the [Unexpected Maker FeatherS3](https://feathers3.io) (ESP32S3). Reads CO2, temperature, and humidity from an Adafruit SCD41 and publishes to MQTT every 60 seconds.

## Hardware

- Unexpected Maker FeatherS3
- Adafruit SCD41 CO2 sensor (connected via STEMMA QT / I2C)
- LiPo battery

## Setup

### 1. Install libraries

Download the [Adafruit CircuitPython bundle](https://circuitpython.org/libraries) matching your installed CircuitPython major version (check `CIRCUITPY/boot_out.txt`) and copy these to `CIRCUITPY/lib/`:

- `adafruit_minimqtt/`
- `adafruit_scd4x.mpy`
- `neopixel.mpy`

### 2. Create `settings.toml`

Copy to `CIRCUITPY/settings.toml` — never committed, device-specific:

```toml
SENSOR_NAME = "office"
WIFI_SSID = ""
WIFI_PASSWORD = ""
MQTT_BROKER = ""
MQTT_PORT = 1883
MQTT_USERNAME = ""
MQTT_PASSWORD = ""
PUSH_INTERVAL = 60
ALTITUDE = 0       # meters above sea level
```

### 3. Deploy firmware

```bash
./tools/deploy.sh
```

The device resets and starts running immediately.

## Monitoring

```bash
./tools/monitor.py
```

Streams serial output to stdout and `/tmp/circuitpy.log`. Ctrl-C stops monitoring (the device keeps running).

## Status LED

| Color | Meaning |
|-------|---------|
| Green | WiFi + MQTT connected |
| Red | Any failure |
| Blue (2s) | Factory reset armed — power cycle to apply |
| Off | Sleeping between readings |

## Sensor Calibration

The SCD41's Automatic Self-Calibration (ASC) assumes weekly exposure to outdoor air (~400 ppm). This firmware disables ASC, which is the correct setting for a permanently-indoor sensor. Without ASC, the factory calibration holds for years.

On first boot (or after a button-triggered reset), the firmware runs `factory_reset()` to clear any accumulated calibration drift from a prior ASC-enabled deployment. Subsequent boots skip the reset.

### Resetting calibration

If the sensor begins reporting obviously wrong values, press the **BOOT button** during the sleep window (LED is off). The LED flashes **blue** to confirm. Power cycle the device — the factory reset runs on next boot, restoring the original calibration baseline.

The button only works during the sleep window between readings. If the LED is green or red, wait for it to turn off, then press.
