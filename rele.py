#!/usr/bin/python
import RPi.GPIO as GPIO
import time
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("relay_control.log"),
        logging.StreamHandler()
    ]
)

# Настройка режима нумерации GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
# Инициализируем список пинов
pinList = [13, 19, 26, 17, 27, 22]

# Время ожидания между операциями в основном цикле (в секундах)
SleepTimeL = 1

def initialize_pins(pins):
    """Настраивает GPIO-пины как выходы с начальным состоянием HIGH."""
    for pin in pins:
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)
        logging.info(f"Пин {pin} настроен как выход с состоянием HIGH")
        time.sleep(0.05)  # Короткая задержка для стабильности

def activate_relay(pin, index):
    """Активирует реле на указанном пине и логирует действие."""
    GPIO.output(pin, GPIO.LOW)  # Включаем реле (если активный LOW)
    logging.info(f"{index}: Реле на пине {pin} активировано (LOW)")
    time.sleep(SleepTimeL)
    
def deactivate_relay(pin, index):
    """Активирует реле на указанном пине и логирует действие."""
    GPIO.output(pin, GPIO.HIGH)  # Включаем реле (если активный LOW)
    logging.info(f"{index}: Реле на пине {pin} deактивировано ()")
    time.sleep(SleepTimeL)

def main():
    """Основная функция для управления реле."""
    try:
        while True:

            initialize_pins(pinList)
            logging.info("Все пины инициализированы. Начинаем последовательную активацию реле.")

            for index, pin in enumerate(pinList, start=1):
                activate_relay(pin, index)

            logging.info("Все реле активированы. Завершаем программу.")
        
            for index, pin in enumerate(pinList, start=1):
                deactivate_relay(pin, index)
        
    
    except KeyboardInterrupt:
        logging.warning("Программа прервана пользователем (KeyboardInterrupt).")
    
    except Exception as e:
        logging.error(f"Возникла ошибка: {e}")
    
    finally:
        GPIO.cleanup()
        logging.info("GPIO очищены. Программа завершена.")

if __name__ == "__main__":
    main()
