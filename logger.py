import logging

def setup_logger():
    logger = logging.getLogger("TemperatureLogger")
    logger.setLevel(logging.INFO)
    
    # Консольний логер
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Форматування логів
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Додаємо консольний хендлер
    logger.addHandler(console_handler)
    
    return logger
