import RPi.GPIO as GPIO
import time
import multiprocessing

# Налаштування GPIO
GPIO.setmode(GPIO.BCM)  # Використовуємо нумерацію GPIO (BCM)
GPIO.setwarnings(False)

class Flasher:
    def __init__(self, pin, on_time, off_time):
        self.pin = pin
        self.on_time = on_time
        self.off_time = off_time
        
        # Налаштовуємо пін як вихідний
        GPIO.setup(self.pin, GPIO.OUT)
        GPIO.output(self.pin, GPIO.LOW)  # Спочатку вимикаємо реле

    # Метод для запуску роботи реле
    def flash(self):
        while True:
            GPIO.output(self.pin, GPIO.HIGH)  # Увімкнути реле
            print(f"Реле на піні {self.pin} увімкнено на {self.on_time} секунд.")
            time.sleep(self.on_time)  # Затримка увімкненого стану
            
            GPIO.output(self.pin, GPIO.LOW)   # Вимкнути реле
            print(f"Реле на піні {self.pin} вимкнено на {self.off_time} секунд.")
            time.sleep(self.off_time)  # Затримка вимкненого стану


if __name__ == "__main__":
    # Створюємо об'єкти Flasher для кожного реле
    relay1 = Flasher(pin=17, on_time=1, off_time=2)  # Реле на GPIO 17
    relay2 = Flasher(pin=27, on_time=2, off_time=3)  # Реле на GPIO 27
    relay3 = Flasher(pin=22, on_time=3, off_time=4)  # Реле на GPIO 22

    # Створюємо процеси для кожного реле
    processes = [
        multiprocessing.Process(target=relay1.flash),
        multiprocessing.Process(target=relay2.flash),
        multiprocessing.Process(target=relay3.flash)
    ]
    
    # Запускаємо процеси
    for process in processes:
        process.start()

    try:
        # Очікуємо завершення процесів
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        # Очищуємо GPIO у випадку завершення програми
        print("Завершення програми...")
        for process in processes:
            process.terminate()
        GPIO.cleanup()  # Очищення GPIO після завершення
