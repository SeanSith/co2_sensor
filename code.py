import os
import time
import board
import adafruit_scd4x
import wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import socketpool
import neopixel

PUSH_INTERVAL = int(os.getenv("PUSH_INTERVAL", 60))  # seconds

# Sensor setup
i2c = board.STEMMA_I2C()
scd4x = adafruit_scd4x.SCD4X(i2c)
scd4x.start_low_periodic_measurement()  # Start once, keep running

# NeoPixel setup
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
pixel.brightness = 0.2

while True:
    # Enable WiFi radio before connecting
    wifi.radio.enabled = True
    # Connect to WiFi
    print(f"Connecting to {os.getenv('WIFI_SSID')}...", end=" ")
    wifi.radio.hostname = os.getenv('SENSOR_NAME')
    try:
        wifi.radio.connect(os.getenv("WIFI_SSID"), os.getenv("WIFI_PASSWORD"))
        print("connected!")
        pixel[0] = (0, 0, 0)  # Off on success
        # MQTT Setup
        pool = socketpool.SocketPool(wifi.radio)
        mqtt_broker = os.getenv("MQTT_BROKER")
        mqtt_port = int(os.getenv("MQTT_PORT", 1883))
        mqtt_username = os.getenv("MQTT_USERNAME")
        mqtt_password = os.getenv("MQTT_PASSWORD")
        sensor_name = os.getenv('SENSOR_NAME')
        mqtt_topic = f"sensors/environmental/{sensor_name}"
        mqtt_client = MQTT.MQTT(
            broker=mqtt_broker,
            port=mqtt_port,
            username=mqtt_username,
            password=mqtt_password,
            socket_pool=pool,
        )

        def connect(mqtt_client, userdata, flags, rc):
            print("connected!")

        def disconnect(mqtt_client, userdata, rc):
            print("Disconnected from MQTT Broker!")

        mqtt_client.on_connect = connect
        mqtt_client.on_disconnect = disconnect

        print(f"Connecting to MQTT broker {mqtt_broker}...", end=" ")
        try:
            mqtt_client.connect()
            pixel[0] = (0, 255, 0)  # Green on WiFi+MQTT success
            try:
                # Wait for sensor data to be ready
                while not scd4x.data_ready:
                    time.sleep(1)

                co2 = scd4x.CO2
                temp = scd4x.temperature
                humidity = scd4x.relative_humidity
                # Publish to MQTT
                payload = '{{"co2": {}, "temperature": {:.2f}, "humidity": {:.2f}}}'.format(co2, temp, humidity)
                try:
                    mqtt_client.publish(mqtt_topic, payload)
                    print(f"Published to {mqtt_topic}: {payload}")
                    pixel[0] = (0, 0, 0)  # Turn off only if everything was successful
                except Exception as e:
                    print(f"[ERROR] MQTT publish to {mqtt_topic} failed!")
                    print(f"[ERROR] Payload: {payload}")
                    print(e)
                    pixel[0] = (255, 0, 0)  # Red on failure
            except Exception as e:
                print()
                print(e)
                pixel[0] = (255, 0, 0)  # Red on failure
        except Exception as e:
            print("failed!")
            print(e)
            pixel[0] = (255, 0, 0)  # Red on failure
    except Exception as e:
        print("failed!")
        print(e)
        pixel[0] = (255, 0, 0)  # Red on failure
    # Wait for next push interval
    print(f"Waiting {PUSH_INTERVAL} seconds before next push...")
    wifi.radio.enabled = False  # Disable WiFi radio to save power
    time.sleep(PUSH_INTERVAL)
