import os
import time
import board
import adafruit_scd4x
import wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import socketpool
import neopixel
import feathers3
import gc

def get_atmospheric_pressure():
    # Placeholder function to return a fixed atmospheric pressure value
    # Replace this with actual sensor reading code if available
    return 1013.25  # Standard atmospheric pressure at sea level in hPa

PUSH_INTERVAL = int(os.getenv("PUSH_INTERVAL", 60))  # seconds

# Cache credentials at module level — avoids allocating new strings each iteration
wifi_ssid = os.getenv("WIFI_SSID")
wifi_password = os.getenv("WIFI_PASSWORD")

# Sensor setup
i2c = board.STEMMA_I2C()
scd4x = adafruit_scd4x.SCD4X(i2c)
scd4x.altitude = int(os.getenv("ALTITUDE", 0))  # Altitude in meters
scd4x.set_ambient_pressure = get_atmospheric_pressure()  # Set ambient pressure in hPa

# MQTT configuration
mqtt_broker =   os.getenv("MQTT_BROKER")
mqtt_port =     int(os.getenv("MQTT_PORT", 1883))
mqtt_username = os.getenv("MQTT_USERNAME")
mqtt_password = os.getenv("MQTT_PASSWORD")
sensor_name =   os.getenv("SENSOR_NAME")
mqtt_topic =    f"sensors/environmental/{sensor_name}"

# NeoPixel setup
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
pixel.brightness = 0.2

# Callbacks at module level — avoids reallocating function objects each iteration
def on_connect(mqtt_client, userdata, flags, rc):
    print("connected!")

def on_disconnect(mqtt_client, userdata, rc):
    print("Disconnected from MQTT Broker!")

while True:
    pixel[0] = (0, 0, 0)  # Reset status LED
    pool = None
    mqtt_client = None

    try:
        # Connect to WiFi
        wifi.radio.enabled = True
        print(f"Connecting to {wifi_ssid}...", end=" ")
        wifi.radio.hostname = sensor_name
        wifi.radio.connect(wifi_ssid, wifi_password)
        print("connected!")

        # MQTT Setup
        pool = socketpool.SocketPool(wifi.radio)
        mqtt_client = MQTT.MQTT(
            broker=mqtt_broker,
            port=mqtt_port,
            username=mqtt_username,
            password=mqtt_password,
            socket_pool=pool,
        )
        mqtt_client.on_connect = on_connect
        mqtt_client.on_disconnect = on_disconnect

        print(f"Connecting to MQTT broker {mqtt_broker}...", end=" ")
        mqtt_client.reconnect()
        pixel[0] = (0, 255, 0)  # Green on WiFi+MQTT connected

        scd4x.measure_single_shot()

        payload = '{{' \
            '"co2":{}' \
            ',"temperature":{:.2f}' \
            ',"humidity":{:.2f}' \
            ',"voltage":{:.2f}' \
            ',"charging":{}' \
            ',"free_memory":{}' \
            ',"uptime":{}' \
        '}}'.format(
            scd4x.CO2,
            scd4x.temperature,
            scd4x.relative_humidity,
            feathers3.get_battery_voltage(),
            1 if feathers3.get_vbus_present() else 0,
            gc.mem_free(),
            time.monotonic()
        )
        mqtt_client.publish(mqtt_topic, payload)
        print(f"Published to {mqtt_topic}: {payload}")
        del payload
        time.sleep(1)  # Allow time for the message to transmit
        pixel[0] = (0, 0, 0)  # Off on full success

    except Exception as e:
        print(e)
        pixel[0] = (255, 0, 0)  # Red on any failure

    finally:
        # Always clean up socket resources, regardless of which step failed.
        # deinit() closes the socket; del releases the Python objects so GC
        # can reclaim their memory on the next gc.collect().
        if mqtt_client is not None:
            try:
                mqtt_client.deinit()
            except Exception:
                pass
            del mqtt_client
        if pool is not None:
            del pool

    gc.collect()
    print(f"Waiting {PUSH_INTERVAL} seconds before next push...")
    wifi.radio.enabled = False  # Disable WiFi radio to save power
    time.sleep(PUSH_INTERVAL)
