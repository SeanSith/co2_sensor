import os
import time
import board
import adafruit_scd4x
import wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import socketpool
import alarm

i2c = board.STEMMA_I2C()
scd4x = adafruit_scd4x.SCD4X(i2c)

# Connect to WiFi
print(f"Connecting to {os.getenv('WIFI_SSID')}...", end=" ")
wifi.radio.hostname = os.getenv('SENSOR_NAME')
wifi_connected = False
try:
    wifi.radio.connect(os.getenv("WIFI_SSID"), os.getenv("WIFI_PASSWORD"))
    print("connected!")
    wifi_connected = True
except Exception as e:
    print("failed!")
    print(e)

PUSH_INTERVAL = int(os.getenv("PUSH_INTERVAL", 60))  # seconds

if wifi_connected:
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
    mqtt_connected = False
    try:
        mqtt_client.connect()
        mqtt_connected = True
    except Exception as e:
        print("failed!")
        print(e)

    if mqtt_connected:
        # Sensor polling
        scd4x.start_low_periodic_measurement()  # Every 30 seconds

        print("Waiting for first measurement....")

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
                time.sleep(1)  # Ensure message is sent before deep sleep
            except Exception as e:
                print("MQTT publish failed!")
                print(e)
        except Exception as e:
            print()
            print(e)

# Always deep sleep at the end
print(f"Entering deep sleep for {PUSH_INTERVAL} seconds...")
time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + PUSH_INTERVAL)
alarm.exit_and_deep_sleep_until_alarms(time_alarm)
