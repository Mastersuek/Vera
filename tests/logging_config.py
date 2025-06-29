import logging
import os
from datetime import datetime

# Создаем директорию для логов тестов
TEST_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'tests')
os.makedirs(TEST_LOG_DIR, exist_ok=True)

# Формат логов
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Настройка основного логгера
def setup_test_logging():
    logger = logging.getLogger('test_logger')
    logger.setLevel(logging.DEBUG)
    
    # Файл логов
    log_file = os.path.join(TEST_LOG_DIR, f'test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
    # Консольный вывод
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Форматтер
    formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
