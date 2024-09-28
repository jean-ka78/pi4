import os

# Унікальні ID ваших датчиків
sensor_1 = '28-0921c00ab497'
sensor_2 = '28-0921c00ef1b1'
sensor_3 = '28-0921c0107bb4'

# Функція для зчитування температури з датчика
def read_temp(sensor_id):
    sensor_file = f'/sys/bus/w1/devices/{sensor_id}/w1_slave'
    
    # Відкриваємо файл з даними датчика
    with open(sensor_file, 'r') as file:
        lines = file.readlines()
        
    # Перевіряємо наявність "YES", що означає успішне зчитування
    if lines[0].strip()[-3:] == 'YES':
        temp_output = lines[1].split('t=')[-1]
        temp_c = float(temp_output) / 1000.0
        return temp_c
    else:
        return None

# Зчитуємо температуру з трьох датчиків
temp_1 = read_temp(sensor_1)
temp_2 = read_temp(sensor_2)
temp_3 = read_temp(sensor_3)

# Виводимо результат
print(f'Temperature from sensor 1: {temp_1:.2f}°C')
print(f'Temperature from sensor 2: {temp_2:.2f}°C')
print(f'Temperature from sensor 3: {temp_3:.2f}°C')
