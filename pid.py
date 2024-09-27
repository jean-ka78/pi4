from venv import logger
from sensor import TemperatureSensor
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import json
import threading
import time
import logging
import os
# from w1thermsensor import W1ThermSensor
# from ds18b20 import TemperatureSensor
from sensor import TemperatureSensor
# import sensor 
# Налаштування логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Налаштування GPIO
GPIO.setmode(GPIO.BCM)

# Визначення пінів (замініть на ваші актуальні пін-коди)
PIN_HIGH = 17       # Пін для клапана HIGH
PIN_LOW = 27        # Пін для клапана LOW
NASOS_OTOP = 22     # Пін для насоса

GPIO.setup(PIN_HIGH, GPIO.OUT)
GPIO.setup(PIN_LOW, GPIO.OUT)
GPIO.setup(NASOS_OTOP, GPIO.OUT)

# Імітація EEPROM за допомогою JSON файлу
EEPROM_FILE = 'eeprom.json'

def load_eeprom():
    try:
        with open(EEPROM_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Початкові значення, якщо файл не існує
        return {
            'nasos_on': False,
            'heat_otop': False,
            'valve_mode': False,
            'temp_min_out': 10.0,
            'temp_max_heat': 60.0,
            'temp_max_out': 80.0,
            'temp_off_otop': 55.0,
            'per_on': 10.0,
            'per_off': 100.0,
            'kof_p': 1.0,
            'kof_i': 1.0,
            'kof_d': 1.0,
            'dead_zone': 0.5,
            'T_bat': 0.0  # Поточна температура (можливо, потрібно оновити)
        }

def save_eeprom(eeprom):
    with open(EEPROM_FILE, 'w') as f:
        json.dump(eeprom, f)

class PIDController(threading.Thread):
    def __init__(self, eeprom, get_temperature_func):
        super().__init__()
        self.eeprom = eeprom
        self.get_temperature = get_temperature_func
        self.running = True

        # Змінні для ПІД-регулювання
        self.T_OUT = 0.0
        self.T_X1 = self.eeprom['temp_min_out']
        self.T_Y1 = self.eeprom['temp_max_heat']
        self.T_X2 = self.eeprom['temp_max_out']
        self.T_Y2 = self.eeprom['temp_off_otop']
        self.T_SET = 0.0

        self.ON_OFF = self.eeprom['heat_otop']
        self.AUTO_HAND = self.eeprom['valve_mode']
        self.HAND_UP = False
        self.HAND_DOWN = False
        self.SET_VALUE = 0.0
        self.PRESENT_VALUE = 0.0
        self.PULSE_100MS = False
        self.CYCLE = self.eeprom['per_on']
        self.VALVE = self.eeprom['per_off']
        self.K_P = self.eeprom['kof_p']
        self.K_I = self.eeprom['kof_i']
        self.K_D = self.eeprom['kof_d']
        self.DEAD_ZONE = self.eeprom['dead_zone']

        # Розбіжності
        self.E_1 = 0.0
        self.E_2 = 0.0
        self.E_3 = 0.0
        self.D_T = 0.0
        self.SUM_D_T = 0.0
        self.TIMER_PID = 0.0
        self.TIMER_PID_UP = 0.0
        self.TIMER_PID_DOWN = 0.0
        self.PID_PULSE = False

        # Тригери та генератори
        self._trgrt1 = False
        self._trgrt1I = False
        self._trgrt2 = False
        self._trgrt2I = False
        self._gtv1 = False
        self._gtv2 = False
        self._gen1I = False
        self._gen1O = False
        self.timer = time.time()

    def run(self):
        while self.running:
            self.loop_pid()
            time.sleep(0.05)  # 50 мс

    def stop(self):
        self.running = False

    def loop_pid(self):
        # Управління тригером 1
        if self._trgrt1I:
            self._trgrt1 = False
        else:
            self._trgrt1 = True
            self._trgrt1I = True
        self._gtv1 = self._trgrt1

        # Генератор
        if not self._gen1I:
            self._gen1I = True
            self._gen1O = True
            self.timer = time.time()

        # Таймер генератора
        if self._gen1I and (time.time() - self.timer) > 0.05:
            self.timer = time.time()
            self._gen1O = not self._gen1O

        # Управління тригером 2
        if self._gen1O:
            if self._trgrt2I:
                self._trgrt2 = False
            else:
                self._trgrt2 = True
                self._trgrt2I = True
        else:
            self._trgrt2 = False
            self._trgrt2I = False
        self._gtv2 = self._trgrt2

        # Розрахунок цільової температури
        self.T_OUT = self.get_temperature()
        self.T_X1 = self.eeprom['temp_min_out']
        self.T_Y1 = self.eeprom['temp_max_heat']
        self.T_X2 = self.eeprom['temp_max_out']
        self.T_Y2 = self.eeprom['temp_off_otop']

        if self.T_OUT <= self.T_X1:
            self.T_SET = self.T_Y1
        elif self.T_X1 < self.T_OUT < self.T_X2:
            if self.T_X1 == self.T_X2:
                self.T_X1 += 0.1
            self.T_SET = (self.T_OUT - self.T_X1) * (self.T_Y1 - self.T_Y2) / (self.T_X1 - self.T_X2) + self.T_Y1
        else:
            self.T_SET = self.T_Y2

        self.SET_VALUE = self.T_SET
        self.PRESENT_VALUE = self.eeprom.get('T_bat', 0.0)  # Отримання поточної температури
        self.PULSE_100MS = self._gtv2
        self.CYCLE = self.eeprom['per_on']
        self.VALVE = self.eeprom['per_off']
        self.K_P = self.eeprom['kof_p']
        self.K_I = self.eeprom['kof_i']
        self.K_D = self.eeprom['kof_d']
        self.DEAD_ZONE = self.eeprom['dead_zone']

        # Розрахунок помилки
        self.E_1 = self.SET_VALUE - self.PRESENT_VALUE

        # Захист від ділення на нуль
        if self.K_I == 0.0:
            self.K_I = 9999.0
        if self.CYCLE == 0.0:
            self.CYCLE = 1.0

        # Обмеження параметрів
        self.K_P = max(min(self.K_P, 99.0), -99.0)
        self.K_I = max(min(self.K_I, 9999.0), 1.0)
        self.K_D = max(min(self.K_D, 9999.0), 0.0)
        self.CYCLE = max(min(self.CYCLE, 25.0), 1.0)
        self.VALVE = max(min(self.VALVE, 250.0), 15.0)

        # Розрахунок ПІД
        if self.PULSE_100MS and self.TIMER_PID == 0.0 and not self.PID_PULSE:
            self.PID_PULSE = True
            self.D_T = self.K_P * (self.E_1 - self.E_2 + self.CYCLE * self.E_2 / self.K_I + self.K_D * (self.E_1 - 2 * self.E_2 + self.E_3) / self.CYCLE) * self.VALVE / 100.0
            self.E_3 = self.E_2
            self.E_2 = self.E_1
            self.SUM_D_T = max(min(self.SUM_D_T + self.D_T, self.VALVE), -self.VALVE)

            if -self.DEAD_ZONE < self.E_1 < self.DEAD_ZONE:
                self.D_T = 0.0
                self.SUM_D_T = 0.0

        # Оновлення таймера
        if self.PULSE_100MS:
            self.TIMER_PID += 0.1

        # ПІД контроль
        if self.ON_OFF and self.AUTO_HAND and self.TIMER_PID >= self.CYCLE:
            self.PID_PULSE = False
            self.TIMER_PID = 0.0
            self.SUM_D_T = 0.0
        elif not self.AUTO_HAND:
            self.PID_PULSE = False
            self.TIMER_PID = 0.0
            self.SUM_D_T = 0.0

        # Управління клапанами
        UP = (((self.SUM_D_T >= self.TIMER_PID and self.SUM_D_T >= 0.5) or self.D_T >= self.CYCLE - 0.5 or self.TIMER_PID_UP >= self.VALVE) and self.AUTO_HAND) or (self.HAND_UP and not self.AUTO_HAND)
        UP = UP and self.ON_OFF and not False  # DOWN ще не визначено

        if self.PULSE_100MS and UP:
            self.TIMER_PID_UP += 0.1
            self.TIMER_PID_UP = min(self.TIMER_PID_UP, self.VALVE)
            GPIO.output(PIN_HIGH, GPIO.LOW)
            logging.info(f"UP")
        else:
            GPIO.output(PIN_HIGH, GPIO.HIGH)

        DOWN = (((self.SUM_D_T <= -self.TIMER_PID and self.SUM_D_T <= -0.5) or self.D_T <= -self.CYCLE + 0.5 or self.TIMER_PID_DOWN >= self.VALVE) and self.AUTO_HAND) or (self.HAND_DOWN and not self.AUTO_HAND)
        DOWN = DOWN and self.ON_OFF and not UP

        if self.PULSE_100MS and DOWN:
            self.TIMER_PID_DOWN += 0.1
            self.TIMER_PID_DOWN = min(self.TIMER_PID_DOWN, self.VALVE)
            GPIO.output(PIN_LOW, GPIO.LOW)
            logging.info(f"DOWN")
        else:
            GPIO.output(PIN_LOW, GPIO.HIGH)

        # Управління насосом
        if self.eeprom['heat_otop']:
            self.turnNasosOn()
        else:
            self.turnNasosOff()

        # Збереження стану в EEPROM
        save_eeprom(self.eeprom)

    def turnNasosOn(self):
        GPIO.output(NASOS_OTOP, GPIO.HIGH)
        self.eeprom['nasos_on'] = True
        logging.info("Насос увімкнено.")

    def turnNasosOff(self):
        GPIO.output(NASOS_OTOP, GPIO.LOW)
        self.eeprom['nasos_on'] = False
        logging.info("Насос вимкнено.")

class MQTTClient:
    def __init__(self, eeprom, pid_controller):
        self.eeprom = eeprom
        self.pid = pid_controller

        # MQTT параметри
        self.MQTT_BROKER = "greenhouse.net.ua"
        self.MQTT_PORT = 1883
        self.MQTT_USER = "mqtt_boyler"
        self.MQTT_PASSWORD = "qwerty"
        self.CLIENT_ID = f"raspi-{os.uname().nodename}"

        # Ініціалізація MQTT клієнта
        self.client = mqtt.Client(self.CLIENT_ID)
        self.client.username_pw_set(self.MQTT_USER, self.MQTT_PASSWORD)

        # Прив'язка колбеків
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        # Підписані теми
        self.topic_handlers = {
            "home/set/boy_on/mode/set": self.handle_boy_mode_set,
            "home/set/boy_on/current-temperature/set": self.handle_boy_temp_set,
            "home/set/heat_on/mode/set": self.handle_heat_mode_set,
            "home/set/boy_on/gis-temperature/get": self.handle_gis_temperature,
            "home/set/heat_on/setpoint-time/cikl": self.handle_heat_cycle_time,
            "home/set/heat_on/setpoint-time/impuls": self.handle_heat_impulse_time,
            "home/set/heat_on/boiler-temperature/off": self.handle_heat_temp_off,
            "home/set/heat_on/temp_min_out": self.handle_temp_min_out,
            "home/set/heat_on/temp_max_out": self.handle_temp_max_out,
            "home/set/heat_on/temp_max_heat": self.handle_temp_max_heat,
            "home/set/heat_on/kof_p": self.handle_kof_p,
            "home/set/heat_on/kof_i": self.handle_kof_i,
            "home/set/heat_on/kof_d": self.handle_kof_d,
            "home/set/heat_on/dead_zone": self.handle_dead_zone,
            "home/set/heat_on/temp_out": self.handle_temp_out,
            "home/set/heat_on/valve/mode": self.handle_valve_mode,
            "home/set/heat_on/hand_up": self.handle_hand_up,
            "home/set/heat_on/hand_down": self.handle_hand_down,
        }

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info("Підключено до MQTT брокера!")
            # Підписка на всі відповідні теми
            for topic in self.topic_handlers.keys():
                client.subscribe(topic)
                logging.info(f"Підписано на тему: {topic}")
        else:
            logging.error(f"Не вдалося підключитися до MQTT брокера, код повернення {rc}")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        message = msg.payload.decode('utf-8').strip()
        logging.debug(f"Отримано повідомлення на тему {topic}: {message}")

        handler = self.topic_handlers.get(topic)
        if handler:
            handler(message)
        else:
            logging.warning(f"Немає обробника для теми: {topic}. Повідомлення: {message}")

    def handle_boy_mode_set(self, message):
        if message == "heat":
            self.eeprom['boy_state'] = True
            logging.info("Режим бойлера встановлено: Heat")
        elif message == "off":
            self.eeprom['boy_state'] = False
            logging.info("Режим бойлера встановлено: Off")
        save_eeprom(self.eeprom)

    def handle_boy_temp_set(self, message):
        try:
            temp_boy = float(message)
            self.eeprom['temp_u'] = temp_boy
            logging.info(f"Уставка бойлера встановлено: {self.eeprom['temp_u']}")
            save_eeprom(self.eeprom)
        except ValueError:
            logging.error(f"Недійсне значення температури бойлера: {message}")

    def handle_heat_mode_set(self, message):
        if message == "heat":
            self.eeprom['heat_otop'] = True
            self.eeprom['summer'] = False
            logging.info("Режим опалення встановлено: Heat")
        elif message == "off":
            self.eeprom['heat_otop'] = False
            logging.info("Режим опалення встановлено: Off")
        elif message == "heat_cool":
            self.eeprom['summer'] = True
            self.eeprom['heat_otop'] = False
            logging.info("Режим опалення встановлено: Heat/Cool")
        save_eeprom(self.eeprom)

    def handle_gis_temperature(self, message):
        try:
            temp_gis = float(message)
            self.eeprom['gis_boy'] = temp_gis
            logging.info(f"Температура GIS встановлено: {self.eeprom['gis_boy']}")
            save_eeprom(self.eeprom)
        except ValueError:
            logging.error(f"Недійсне значення температури GIS: {message}")

    def handle_heat_cycle_time(self, message):
        try:
            time_cikl = float(message)
            self.eeprom['per_off'] = time_cikl
            logging.info(f"Час циклу опалення встановлено: {self.eeprom['per_off']}")
            save_eeprom(self.eeprom)
        except ValueError:
            logging.error(f"Недійсне значення часу циклу: {message}")

    def handle_heat_impulse_time(self, message):
        try:
            time_imp = float(message)
            self.eeprom['per_on'] = time_imp
            logging.info(f"Час імпульсу опалення встановлено: {self.eeprom['per_on']}")
            save_eeprom(self.eeprom)
        except ValueError:
            logging.error(f"Недійсне значення часу імпульсу: {message}")

    def handle_heat_temp_off(self, message):
        try:
            temp_off = float(message)
            self.eeprom['temp_off_otop'] = temp_off
            logging.info(f"Температура вимкнення опалення встановлено: {self.eeprom['temp_off_otop']}")
            save_eeprom(self.eeprom)
        except ValueError:
            logging.error(f"Недійсне значення температури вимкнення опалення: {message}")

    def handle_temp_min_out(self, message):
        try:
            temp_min_out = float(message)
            self.eeprom['temp_min_out'] = temp_min_out
            logging.info(f"Мінімальна температура на виході встановлено: {self.eeprom['temp_min_out']}")
            save_eeprom(self.eeprom)
        except ValueError:
            logging.error(f"Недійсне значення мінімальної температури на виході: {message}")

    def handle_temp_max_out(self, message):
        try:
            temp_max_out = float(message)
            self.eeprom['temp_max_out'] = temp_max_out
            logging.info(f"Максимальна температура на виході встановлено: {self.eeprom['temp_max_out']}")
            save_eeprom(self.eeprom)
        except ValueError:
            logging.error(f"Недійсне значення максимальної температури на виході: {message}")

    def handle_temp_max_heat(self, message):
        try:
            temp_max_heat = float(message)
            self.eeprom['temp_max_heat'] = temp_max_heat
            logging.info(f"Максимальна температура опалення встановлено: {self.eeprom['temp_max_heat']}")
            save_eeprom(self.eeprom)
        except ValueError:
            logging.error(f"Недійсне значення максимальної температури опалення: {message}")

    def handle_kof_p(self, message):
        try:
            kof_p = float(message)
            self.eeprom['kof_p'] = kof_p
            logging.info(f"KOF_P встановлено: {self.eeprom['kof_p']}")
            save_eeprom(self.eeprom)
        except ValueError:
            logging.error(f"Недійсне значення KOF_P: {message}")

    def handle_kof_i(self, message):
        try:
            kof_i = float(message)
            self.eeprom['kof_i'] = kof_i
            logging.info(f"KOF_I встановлено: {self.eeprom['kof_i']}")
            save_eeprom(self.eeprom)
        except ValueError:
            logging.error(f"Недійсне значення KOF_I: {message}")

    def handle_kof_d(self, message):
        try:
            kof_d = float(message)
            self.eeprom['kof_d'] = kof_d
            logging.info(f"KOF_D встановлено: {self.eeprom['kof_d']}")
            save_eeprom(self.eeprom)
        except ValueError:
            logging.error(f"Недійсне значення KOF_D: {message}")

    def handle_dead_zone(self, message):
        try:
            dead_zone = float(message)
            self.eeprom['dead_zone'] = dead_zone
            logging.info(f"Dead Zone встановлено: {self.eeprom['dead_zone']}")
            save_eeprom(self.eeprom)
        except ValueError:
            logging.error(f"Недійсне значення Dead Zone: {message}")

    def handle_temp_out(self, message):
        try:
            temp_out = float(message)
            self.eeprom['temp_out'] = temp_out
            logging.info(f"Температура на виході встановлено: {self.eeprom['temp_out']}")
            save_eeprom(self.eeprom)
        except ValueError:
            logging.error(f"Недійсне значення температури на виході: {message}")

    def handle_valve_mode(self, message):
        if message == "on":
            self.eeprom['valve_mode'] = True
            logging.info("Режим клапана встановлено: On")
        elif message == "off":
            self.eeprom['valve_mode'] = False
            logging.info("Режим клапана встановлено: Off")
        save_eeprom(self.eeprom)

    def handle_hand_up(self, message):
        if message == "on":
            self.pid.HAND_UP = True
            logging.info("Ручний підйом увімкнено.")
        elif message == "off":
            self.pid.HAND_UP = False
            logging.info("Ручний підйом вимкнено.")
        save_eeprom(self.eeprom)

    def handle_hand_down(self, message):
        if message == "on":
            self.pid.HAND_DOWN = True
            logging.info("Ручне опускання увімкнено.")
        elif message == "off":
            self.pid.HAND_DOWN = False
            logging.info("Ручне опускання вимкнено.")
        save_eeprom(self.eeprom)

    def start(self):
        try:
            self.client.connect(self.MQTT_BROKER, self.MQTT_PORT, 60)
        except Exception as e:
            logging.error(f"Не вдалося підключитися до MQTT брокера: {e}")
            return

        # Запуск MQTT клієнта у фоновому режимі
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

def read_temperatur():
    base_dir = '/sys/bus/w1/devices/'
    device_folder = [f for f in os.listdir(base_dir) if f.startswith('28')][0]
    device_file = f'{base_dir}{device_folder}/w1_slave'

    try:
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
    except Exception as e:
        logging.error(f"Помилка зчитування температури: {e}")
    return None

def moving_average_filter(new_value, smoothed_value):
    return 0.9 * smoothed_value + 0.1 * new_value

def get_current_temperature():
    temperature = read_temperature()
    if temperature is not None:
        logging.info(f"Поточна температура: {temperature}°C")
    else:
        logging.warning("Не вдалося зчитати температуру.")
    return temperature if temperature is not None else 0.0  # Повертаємо 0.0, якщо зчитування не вдалося
def read_temperature():
    sensor = TemperatureSensor()
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
                # logger.info(f"Raw Temperature: {raw_temperature}")
                # logger.info(f"Smoothed Temperature: {round(smoothed_temperature, 2)}")
                # mqtt_client.publish(str(round(smoothed_temperature, 2)))

            time.sleep(1)
    except Exception as e:
        logging.error(f"Помилка зчитування температури: {e}")
    return None
    
def main():
    # Завантаження стану з EEPROM
    eeprom = load_eeprom()

    # Ініціалізація ПІД-регулятора
    pid_controller = PIDController(eeprom, get_current_temperature)
    pid_controller.start()

    # Ініціалізація MQTT клієнта
    mqtt_client = MQTTClient(eeprom, pid_controller)
    mqtt_client.start()

    try:
        while True:
            time.sleep(1)  # Основний цикл може виконувати інші завдання
    except KeyboardInterrupt:
        logging.info("Вимикається...")
    finally:
        pid_controller.stop()
        mqtt_client.stop()
        GPIO.cleanup()

if __name__ == "__main__":
    main()
