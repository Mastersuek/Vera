import logging
import logging.handlers
import os
import gzip
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import threading
import time

class GZipRotator:
    """Сжимает логи в .gz после ротации"""
    @staticmethod
    def namer(name: str) -> str:
        return name + ".gz"

    @staticmethod
    def rotator(source: str, dest: str) -> None:
        with open(source, 'rb') as f_in:
            with gzip.open(dest, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(source)

class LogCleanupScheduler:
    """Планировщик очистки старых логов"""
    def __init__(self, log_dir: str, max_days: int = 7):
        self.log_dir = Path(log_dir)
        self.max_days = max_days
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Запуск планировщика очистки"""
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_cleanup, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Остановка планировщика"""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join()

    def _run_cleanup(self) -> None:
        """Цикл очистки старых логов"""
        while not self._stop_event.is_set():
            try:
                self._cleanup_old_logs()
            except Exception as e:
                logging.error(f"Ошибка при очистке логов: {e}")
            
            # Проверяем раз в час
            self._stop_event.wait(3600)

    def _cleanup_old_logs(self) -> None:
        """Удаление логов старше max_days"""
        if not self.log_dir.exists():
            return
            
        cutoff_time = time.time() - (self.max_days * 86400)
        
        for log_file in self.log_dir.glob('*'):
            if log_file.is_file() and log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                except Exception as e:
                    logging.error(f"Не удалось удалить старый лог {log_file}: {e}")

class SemanticLogger:
    """Настройка системы логирования для проекта"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, log_dir: str = "logs", max_log_size: int = 10, backup_count: int = 5, max_days: int = 7):
        if self._initialized:
            return
            
        self.log_dir = Path(log_dir)
        self.max_log_size = max_log_size * 1024 * 1024  # в МБ
        self.backup_count = backup_count
        self.max_days = max_days
        
        # Создаем директорию для логов, если её нет
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Настройка корневого логгера
        self.root_logger = logging.getLogger()
        self.root_logger.setLevel(logging.INFO)
        
        # Формат логов
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Обработчик для консоли
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.root_logger.addHandler(console_handler)
        
        # Обработчик для файла с ротацией
        log_file = self.log_dir / 'semantic_core.log'
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.max_log_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.rotator = GZipRotator.rotator
        file_handler.namer = GZipRotator.namer
        self.root_logger.addHandler(file_handler)
        
        # Запускаем планировщик очистки
        self.cleaner = LogCleanupScheduler(str(self.log_dir), max_days)
        self.cleaner.start()
        
        self._initialized = True
        logging.info("Система логирования инициализирована")
    
    def get_logger(self, name: str) -> logging.Logger:
        """Получить именованный логгер"""
        return logging.getLogger(name)
    
    def cleanup(self) -> None:
        """Очистка ресурсов"""
        self.cleaner.stop()
        logging.shutdown()

def get_logger(name: str = None) -> logging.Logger:
    """Получить логгер по имени (синглтон)"""
    if not hasattr(get_logger, '_logger'):
        get_logger._logger = SemanticLogger()
    
    if name is None:
        return get_logger._logger.root_logger
    return get_logger._logger.get_logger(name)

# Инициализация глобального логгера при импорте
logger = get_logger(__name__)

if __name__ == "__main__":
    # Пример использования
    logger = get_logger("test")
    logger.info("Тестовое сообщение")
    
    try:
        1 / 0
    except Exception as e:
        logger.exception("Произошла ошибка")
