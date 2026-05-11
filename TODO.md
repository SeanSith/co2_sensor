# TODO

## Medium Priority

### Simplify Infrastructure: Drop Mosquitto + Telegraf, Use Prometheus Pushgateway
The current pipeline has four hops: **Sensor → Mosquitto → Telegraf → Prometheus**. Since this sensor is the only MQTT publisher, both Mosquitto and Telegraf can be eliminated.

**Proposed pipeline: Sensor → Pushgateway → Prometheus**

*Firmware changes (`code.py`):*
- Remove `adafruit_minimqtt` dependency (and `lib/adafruit_minimqtt/`)
- Add `adafruit_requests` (already in the Adafruit bundle)
- Replace the MQTT connect/publish block with a single HTTP PUT to the Pushgateway using Prometheus text format:
  ```
  co2_ppm{sensor="office"} 412
  temperature_celsius{sensor="office"} 22.50
  relative_humidity{sensor="office"} 48.10
  battery_voltage{sensor="office"} 3.85
  charging{sensor="office"} 0
  free_memory_bytes{sensor="office"} 142336
  uptime_seconds{sensor="office"} 3720.0
  ```
  PUT to `http://{PUSHGATEWAY_HOST}/metrics/job/co2_sensor/instance/{SENSOR_NAME}`
- Update `settings.toml`: replace `MQTT_*` keys with `PUSHGATEWAY_HOST`

*Server-side changes:*
- Add `prom/pushgateway` container (no config file needed — exposes `:9091` by default)
- Update Prometheus scrape config to target the Pushgateway instead of the Telegraf endpoint
- Remove Telegraf and Mosquitto containers/services

*Staleness caveat:* The Pushgateway retains the last pushed value indefinitely. If the sensor goes offline, Prometheus continues seeing stale metrics. Mitigate by alerting on `push_time_seconds{job="co2_sensor"} > PUSH_INTERVAL * 3` rather than on the metric value itself. Alternatively, the sensor can send a DELETE request to the Pushgateway before sleeping (clears the metric so Prometheus sees no data instead of stale data) — but this only helps if the sensor shuts down cleanly.

## Low Priority

### Watchdog / Hardware Reset on Hang
CircuitPython supports a software watchdog via `microcontroller.watchdog`. If the device ever hangs mid-cycle (e.g., WiFi connect blocks forever), a watchdog reset would recover it automatically without manual power cycling.
```python
import microcontroller
microcontroller.watchdog.timeout = 30  # seconds
microcontroller.watchdog.mode = microcontroller.watchdog.WatchDogMode.RESET
# feed it each successful cycle: microcontroller.watchdog.feed()
```
