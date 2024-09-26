import time
import os
import paho.mqtt.client as mqtt

# Налаштування MQTT
MQTT_BROKER = "greenhouse.net.ua"
MQTT_TOPIC = "aparts/temp_out"
MQTT_USER = "mqtt"
MQTT_PASSWORD = "qwerty"
CLIENT_ID = f"raspi-{os.uname().nodename}"

# Функція з'єднання з MQTT брокером
def connect_mqtt():
    client = mqtt.Client(CLIENT_ID)
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.connect(MQTT_BROKER, 1883, 60)
    return client

# Функція для читання температури з файлу 1-Wire
def read_temperature():
    base_dir = '/sys/bus/w1/devices/'
    device_folder = [f for f in os.listdir(base_dir) if f.startswith('28')][0]
    device_file = f'{base_dir}{device_folder}/w1_slave'

    with open(device_file, 'r') as f:
        lines = f.readlines()

    # Перевіряємо, чи є "YES" у першому рядку, що свідчить про коректне зчитування
    if lines[0].strip()[-3:] == 'YES':
        # Зчитуємо температуру з другого рядка
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            temp_string = lines[1][equals_pos + 2:]
            temperature = float(temp_string) / 1000.0
            return temperature
    return None

# Фільтр ковзного середнього для згладжування показників температури
def moving_average_filter(new_value, smoothed_value):
    return 0.9 * smoothed_value + 0.1 * new_value

# Основна програма
def main():
    client = connect_mqtt()

    try:
        # Ініціалізація першим виміряним значенням температури
        initial_temperature = read_temperature()
        if initial_temperature is None:
            print("No sensors found.")
            return

        smoothed_temperature = initial_temperature  # Використовуємо перше значення для згладження

        while True:
            raw_temperature = read_temperature()

            if raw_temperature is not None:
                smoothed_temperature = moving_average_filter(raw_temperature, smoothed_temperature)
                print("Raw Temperature:", raw_temperature)
                print("Smoothed Temperature:", round(smoothed_temperature, 2))

                try:
                    client.publish(MQTT_TOPIC, str(round(smoothed_temperature, 2)))
                except Exception as e:
                    print('MQTT publish failed, reconnecting to MQTT broker:', e)
                    client.reconnect()

            time.sleep(1)

    except KeyboardInterrupt:
        client.disconnect()
        print("Program terminated")

# Виклик основної програми
if __name__ == "__main__":
    main()
