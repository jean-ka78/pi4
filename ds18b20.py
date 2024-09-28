import time
import os
import paho.mqtt.client as mqtt
import threading
import logging

class TemperatureSensor:
    def __init__(self, broker, port, topic, user, password, client_id=None, interval=1):
        """
        Ініціалізація температурного сенсора та MQTT-підключення.

        :param broker: Адреса MQTT брокера
        :param port: Порт MQTT брокера
        :param topic: Тема для публікації температури
        :param user: Ім'я користувача MQTT
        :param password: Пароль MQTT
        :param client_id: Ідентифікатор клієнта MQTT
        :param interval: Інтервал зчитування температури у секундах
        """
        self.broker = broker
        self.port = port
        self.topic = topic
        self.user = user
        self.password = password
        self.client_id = client_id if client_id else f"raspi-{os.uname().nodename}"
        self.interval = interval
        self.smoothed_temperature = None
        self.running = False

        # Налаштування логування
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

        # Ініціалізація MQTT клієнта
        self.client = mqtt.Client(self.client_id)
        self.client.username_pw_set(self.user, self.password)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect

    def connect_mqtt(self):
        """
        Підключення до MQTT брокера.
        """
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            logging.info("Підключено до MQTT брокера.")
        except Exception as e:
            logging.error(f"Не вдалося підключитися до MQTT брокера: {e}")
            self.reconnect()

    def reconnect(self):
        """
        Спроба повторного підключення до MQTT брокера у випадку помилки.
        """
        while True:
            try:
                self.client.reconnect()
                logging.info("Повторно підключено до MQTT брокера.")
                break
            except Exception as e:
                logging.error(f"Повторне підключення не вдалося: {e}")
                time.sleep(5)

    def on_connect(self, client, userdata, flags, rc):
        """
        Колбек при успішному підключенні до MQTT брокера.
        """
        if rc == 0:
            logging.info("Успішно підключено до MQTT брокера.")
        else:
            logging.error(f"Не вдалося підключитися до MQTT брокера, код {rc}")

    def on_disconnect(self, client, userdata, rc):
        """
        Колбек при відключенні від MQTT брокера.
        """
        logging.warning("Відключено від MQTT брокера.")
        self.reconnect()

    def read_temperature(self):
        """
        Зчитування температури з файлу 1-Wire DS18B20.

        :return: Поточна температура або None у випадку помилки
        """
        base_dir = '/sys/bus/w1/devices/'
        try:
            device_folders = [f for f in os.listdir(base_dir) if f.startswith('28')]
            if not device_folders:
                logging.error("Не знайдено датчиків температури.")
                return None
            device_folder = device_folders[0]
            device_file = f'{base_dir}{device_folder}/w1_slave'

            with open(device_file, 'r') as f:
                lines = f.readlines()

            # Перевіряємо, чи є "YES" у першому рядку
            if lines[0].strip().endswith('YES'):
                # Зчитуємо температуру з другого рядка
                equals_pos = lines[1].find('t=')
                if equals_pos != -1:
                    temp_string = lines[1][equals_pos + 2:]
                    temperature = float(temp_string) / 1000.0
                    return temperature
            else:
                logging.warning("Некоректне зчитування температури.")
        except Exception as e:
            logging.error(f"Помилка зчитування температури: {e}")
        return None

    def moving_average_filter(self, new_value, smoothed_value):
        """
        Застосування фільтру ковзного середнього для згладжування показників температури.

        :param new_value: Нове значення температури
        :param smoothed_value: Згладжене значення температури
        :return: Оновлене згладжене значення температури
        """
        return 0.9 * smoothed_value + 0.1 * new_value

    def publish_temperature(self):
        """
        Зчитування, фільтрування та публікація температури у MQTT брокер.
        """
        raw_temperature = self.read_temperature()
        if raw_temperature is not None:
            if self.smoothed_temperature is None:
                self.smoothed_temperature = raw_temperature
            else:
                self.smoothed_temperature = self.moving_average_filter(raw_temperature, self.smoothed_temperature)
            logging.info(f"Raw Temperature: {raw_temperature}°C")
            logging.info(f"Smoothed Temperature: {round(self.smoothed_temperature, 2)}°C")
            try:
                self.client.publish(self.topic, str(round(self.smoothed_temperature, 2)))
            except Exception as e:
                logging.error(f"Не вдалося опублікувати у MQTT брокер: {e}")
                self.reconnect()
        else:
            logging.warning("Не вдалося зчитати температуру.")
        time.sleep(self.interval)

    def start_publishing(self):
        """
        Запуск циклу публікації температури у окремому потоці.
        """
        self.running = True
        thread = threading.Thread(target=self.run)
        thread.start()

    def run(self):
        """
        Основний цикл зчитування та публікації температури.
        """
        # Ініціалізація першого значення температури
        initial_temperature = self.read_temperature()
        if initial_temperature is None:
            logging.error("Не вдалося ініціалізувати сенсор температури.")
            return
        self.smoothed_temperature = initial_temperature
        logging.info(f"Початкова температура: {self.smoothed_temperature}°C")

        while self.running:
            self.publish_temperature()

    def stop_publishing(self):
        """
        Зупинка циклу публікації температури.
        """
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()
        logging.info("Зупинено публікацію температури.")

    def run_forever(self):
        """
        Запуск публікації температури.
        """
        self.connect_mqtt()
        self.start_publishing()

    def shutdown(self):
        """
        Коректне завершення роботи класу.
        """
        self.stop_publishing()

# Приклад використання
if __name__ == "__main__":
    sensor = TemperatureSensor(
        broker="greenhouse.net.ua",
        port=1883,
        topic="aparts/temp",
        user="mqtt",
        password="qwerty",
        client_id=f"raspi-{os.uname().nodename}",
        interval=1
    )
    try:
        sensor.run_forever()
    except KeyboardInterrupt:
        sensor.shutdown()
        logging.info("Програма завершена.")
