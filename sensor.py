import os

class TemperatureSensor:
    def __init__(self, sensor_id='28'):
        self.base_dir = '/sys/bus/w1/devices/'
        self.sensor_id = sensor_id
        self.device_file = self._get_device_file()

    def _get_device_file(self):
        device_folder = [f for f in os.listdir(self.base_dir) if f.startswith(self.sensor_id)][0]
        return f'{self.base_dir}{device_folder}/w1_slave'

    def read_temperature(self):
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
            print(f"Error reading temperature: {e}")
        return None
