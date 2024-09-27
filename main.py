import time
import os
from sensor import TemperatureSensor
from mqtt_client import MQTTClient
from logger import setup_logger

# Налаштування MQTT
MQTT_BROKER = "greenhouse.net.ua"
MQTT_TOPIC = "aparts/temp_out"
MQTT_USER = "mqtt"
MQTT_PASSWORD = "qwerty"
CLIENT_ID = f"raspi-{os.uname().nodename}"

# Ініціалізація логера
logger = setup_logger()

def moving_average_filter(new_value, smoothed_value):
    return 0.9 * smoothed_value + 0.1 * new_value

def main():
    # Створюємо об'єкт сенсору
    sensor = TemperatureSensor()

    # Підключаємося до MQTT
    mqtt_client = MQTTClient(MQTT_BROKER, MQTT_TOPIC, MQTT_USER, MQTT_PASSWORD, CLIENT_ID)

    try:
        # Ініціалізація першим виміряним значенням температури
        initial_temperature = sensor.read_temperature()
        if initial_temperature is None:
            logger.error("No sensors found.")
            return

        smoothed_temperature = initial_temperature

        while True:
            raw_temperature = sensor.read_temperature()

            if raw_temperature is not None:
                smoothed_temperature = moving_average_filter(raw_temperature, smoothed_temperature)
                logger.info(f"Raw Temperature: {raw_temperature}")
                logger.info(f"Smoothed Temperature: {round(smoothed_temperature, 2)}")

                # mqtt_client.publish(str(round(smoothed_temperature, 2)))

            time.sleep(1)

    except KeyboardInterrupt:
        # mqtt_client.disconnect()
        logger.info("Program terminated")

if __name__ == "__main__":
    main()
