import paho.mqtt.client as mqtt
import logging

# Налаштування логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GreenhouseController:
    def __init__(self):
        # Ініціалізація змінних стану
        self.eeprom = {
            'boy_state': False,
            'temp_u': 0.0,
            'heat_state': False,
            'summer': False,
            'gis_boy': 0.0,
            'per_off': 0,
            'per_on': 0,
            'temp_off_otop': 0.0,
            'temp_min_out': 0.0,
            'temp_max_out': 0.0,
            'temp_max_heat': 0.0,
            'kof_p': 0.0,
            'kof_i': 0.0,
            'kof_d': 0.0,
            'dead_zone': 0.0,
            'valve_mode': False,
        }
        self.High = {'OffTime': 0, 'OnTime': 0}
        self.Low = {'OffTime': 0, 'OnTime': 0}
        self.T_out = 0.0
        self.hand_up = False
        self.hand_down = False

        # Визначення MQTT тем та їх обробників
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
            "home/boy_on/current-temperature/get": self.handle_boy_curr_temp,
            "home/heat_on/current-temperature/get": self.handle_bat_curr_temp,
            "home/heat_on/current-temperature_koll": self.handle_heat_curr_temp,

        }

    def handle_boy_mode_set(self, message):
        if message == "heat":
            self.eeprom['boy_state'] = True
        elif message == "off":
            self.eeprom['boy_state'] = False
        logging.info(f"Режим бойлера встановлено: {self.eeprom['boy_state']}")

    def handle_boy_temp_set(self, message):
        try:
            temp_boy = float(message)
            self.eeprom['temp_u'] = temp_boy
            logging.info(f"Уставка бойлера: {self.eeprom['temp_u']}")
        except ValueError:
            logging.error(f"Недійсне значення температури: {message}")

    def handle_heat_mode_set(self, message):
        if message == "heat":
            self.eeprom['heat_state'] = True
            self.eeprom['summer'] = False
        elif message == "off":
            self.eeprom['heat_state'] = False
        elif message == "heat_cool":
            self.eeprom['summer'] = True
            self.eeprom['heat_state'] = False
        logging.info(f"Режим опалення встановлено: heat_state={self.eeprom['heat_state']}, summer={self.eeprom['summer']}")

    def handle_gis_temperature(self, message):
        try:
            temp_gis = float(message)
            self.eeprom['gis_boy'] = temp_gis
            logging.info(f"Температура GIS: {self.eeprom['gis_boy']}")
        except ValueError:
            logging.error(f"Недійсне значення температури GIS: {message}")

    def handle_heat_cycle_time(self, message):
        try:
            time_cikl = int(message)
            self.eeprom['per_off'] = time_cikl
            self.High['OffTime'] = time_cikl
            self.Low['OffTime'] = time_cikl
            logging.info(f"Час циклу опалення: {self.eeprom['per_off']}")
        except ValueError:
            logging.error(f"Недійсне значення часу циклу: {message}")

    def handle_heat_impulse_time(self, message):
        try:
            time_imp = int(message)
            self.eeprom['per_on'] = time_imp
            self.High['OnTime'] = time_imp
            self.Low['OnTime'] = time_imp
            logging.info(f"Час імпульсу опалення: {self.eeprom['per_on']}")
        except ValueError:
            logging.error(f"Недійсне значення часу імпульсу: {message}")

    def handle_heat_temp_off(self, message):
        try:
            temp_off = float(message)
            self.eeprom['temp_off_otop'] = temp_off
            logging.info(f"Температура вимкнення опалення: {self.eeprom['temp_off_otop']}")
        except ValueError:
            logging.error(f"Недійсне значення температури вимкнення: {message}")

    def handle_temp_min_out(self, message):
        try:
            temp_min_out = float(message)
            self.eeprom['temp_min_out'] = temp_min_out
            logging.info(f"Мінімальна температура на виході: {self.eeprom['temp_min_out']}")
        except ValueError:
            logging.error(f"Недійсне значення мінімальної температури на виході: {message}")

    def handle_temp_max_out(self, message):
        try:
            temp_max_out = float(message)
            self.eeprom['temp_max_out'] = temp_max_out
            logging.info(f"Максимальна температура на виході: {self.eeprom['temp_max_out']}")
        except ValueError:
            logging.error(f"Недійсне значення максимальної температури на виході: {message}")

    def handle_temp_max_heat(self, message):
        try:
            temp_max_heat = float(message)
            self.eeprom['temp_max_heat'] = temp_max_heat
            logging.info(f"Максимальна температура опалення: {self.eeprom['temp_max_heat']}")
        except ValueError:
            logging.error(f"Недійсне значення максимальної температури опалення: {message}")

    def handle_kof_p(self, message):
        try:
            kof_p = float(message)
            self.eeprom['kof_p'] = kof_p
            logging.info(f"KOF_P: {self.eeprom['kof_p']}")
        except ValueError:
            logging.error(f"Недійсне значення KOF_P: {message}")

    def handle_kof_i(self, message):
        try:
            kof_i = float(message)
            self.eeprom['kof_i'] = kof_i
            logging.info(f"KOF_I: {self.eeprom['kof_i']}")
        except ValueError:
            logging.error(f"Недійсне значення KOF_I: {message}")

    def handle_kof_d(self, message):
        try:
            kof_d = float(message)
            self.eeprom['kof_d'] = kof_d
            logging.info(f"KOF_D: {self.eeprom['kof_d']}")
        except ValueError:
            logging.error(f"Недійсне значення KOF_D: {message}")

    def handle_dead_zone(self, message):
        try:
            dead_zone = float(message)
            self.eeprom['dead_zone'] = dead_zone
            logging.info(f"Dead Zone: {self.eeprom['dead_zone']}")
        except ValueError:
            logging.error(f"Недійсне значення Dead Zone: {message}")

    def handle_temp_out(self, message):
        try:
            temp_out = float(message)
            self.T_out = temp_out
            logging.info(f"Температура на виході: {self.T_out}")
        except ValueError:
            logging.error(f"Недійсне значення температури на виході: {message}")
    
    def handle_boy_curr_temp(self, message):
        try:
            temp_boy = float(message)
            self.T_boy = temp_boy
            logging.info(f"Температура бойлера: {self.T_boy}")
        except ValueError:
            logging.error(f"Недійсне значення температури бойлера: {message}")

    def handle_bat_curr_temp(self, message):
        try:
            temp_bat = float(message)
            self.T_bat = temp_bat
            logging.info(f"Температура батарей: {self.T_bat}")
        except ValueError:
            logging.error(f"Недійсне значення температури батарей: {message}")
    
    def handle_heat_curr_temp(self, message):
        try:
            temp_heat = float(message)
            self.T_heat = temp_heat
            logging.info(f"Температура коллектора: {self.T_heat}")
        except ValueError:
            logging.error(f"Недійсне значення температури коллектора: {message}")

    def handle_valve_mode(self, message):
        if message == "on":
            self.eeprom['valve_mode'] = True
        elif message == "off":
            self.eeprom['valve_mode'] = False
        logging.info(f"Режим клапана: {self.eeprom['valve_mode']}")

    def handle_hand_up(self, message):
        if message == "on":
            self.hand_up = True
        elif message == "off":
            self.hand_up = False
        logging.info(f"Ручний підйом: {self.hand_up}")

    def handle_hand_down(self, message):
        if message == "on":
            self.hand_down = True
        elif message == "off":
            self.hand_down = False
        logging.info(f"Ручне опускання: {self.hand_down}")

    def handle_message(self, topic, message):
        handler = self.topic_handlers.get(topic)
        if handler:
            handler(message)
        else:
            logging.warning(f"Немає обробника для теми: {topic}. Повідомлення: {message}")

def main():
    controller = GreenhouseController()

    # Параметри MQTT
    mqtt_server = "greenhouse.net.ua"
    mqtt_port = 1883
    mqtt_user = "mqtt_boyler"
    mqtt_pass = "qwerty"

    # Ініціалізація MQTT клієнта
    client = mqtt.Client()

    # Встановлення імені користувача та пароля
    client.username_pw_set(mqtt_user, mqtt_pass)

    # Визначення колбеку для з'єднання
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            logging.info("Підключено до MQTT брокера!")
            # Підписка на всі відповідні теми
            for topic in controller.topic_handlers.keys():
                client.subscribe(topic)
                logging.info(f"Підписано на тему: {topic}")
        else:
            logging.error(f"Не вдалося підключитися, код повернення {rc}")

    # Визначення колбеку для вхідних повідомлень
    def on_message(client, userdata, msg):
        topic = msg.topic
        message = msg.payload.decode('utf-8').strip()
        logging.debug(f"Отримано повідомлення на тему {topic}: {message}")
        controller.handle_message(topic, message)

    # Прив'язка колбеків
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        # Підключення до MQTT брокера
        client.connect(mqtt_server, mqtt_port, 60)
    except Exception as e:
        logging.error(f"Не вдалося підключитися до MQTT брокера: {e}")
        return

    # Блокуючий виклик, який обробляє мережевий трафік, викликає колбеки та обробляє повторне підключення.
    client.loop_forever()

if __name__ == "__main__":
    main()
