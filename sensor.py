import os

class TemperatureSensor:
    def __init__(self, sensor_id):
        self.base_dir = '/sys/bus/w1/devices/'
        self.sensor_id = sensor_id
        self.device_file = self._get_device_file()

    def _get_device_file(self):
        try:
            device_folder = [f for f in os.listdir(self.base_dir) if f.startswith(self.sensor_id)][0]
            return f'{self.base_dir}{device_folder}/w1_slave'
        except IndexError:
            print(f"Sensor {self.sensor_id} not found.")
            return None

    def read_temperature(self):
        if self.device_file is None:
            return None

        try:
            with open(self.device_file, 'r') as f:
                lines = f.readlines()

            # Перевірка на коректність зчитування (YES)
            if lines[0].strip()[-3:] == 'YES':
                # Зчитуємо температуру
                equals_pos = lines[1].find('t=')
                if equals_pos != -1:
                    temp_string = lines[1][equals_pos + 2:]
                    temperature = float(temp_string) / 1000.0
                    return temperature
        except Exception as e:
            print(f"Error reading temperature from sensor {self.sensor_id}: {e}")
        return None
"""
# Унікальні ID ваших датчиків
sensor_1 = TemperatureSensor('28-0921c00ab497')
sensor_2 = TemperatureSensor('28-0921c00ef1b1')
sensor_3 = TemperatureSensor('28-0921c0107bb4')

# Зчитування температури з кожного сенсора
print(f"Temperature from sensor 1: {sensor_1.read_temperature()} °C")
print(f"Temperature from sensor 2: {sensor_2.read_temperature()} °C")
print(f"Temperature from sensor 3: {sensor_3.read_temperature()} °C")
"""