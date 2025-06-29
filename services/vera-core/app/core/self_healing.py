import os
import time
import signal
import subprocess
import sys
import psutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Tuple
from datetime import datetime, timedelta
import json
import traceback
import platform
from concurrent.futures import ThreadPoolExecutor

from ..core.logging import get_logger

logger = get_logger(__name__)


class ServiceHealth:
    """Класс для мониторинга состояния сервиса"""
    
    def __init__(self, service_name: str, max_restarts: int = 3, restart_window: int = 3600):
        self.service_name = service_name
        self.max_restarts = max_restarts
        self.restart_window = restart_window  # в секундах
        self.restart_times: List[float] = []
        self.health_metrics: Dict[str, Any] = {
            'start_time': time.time(),
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'last_error': None,
            'last_error_time': None,
            'avg_response_time': 0.0,
            'response_times': []
        }
        self._lock = threading.Lock()
    
    def record_request(self, success: bool, response_time: float = 0.0, error: Exception = None):
        """Записывает метрики запроса"""
        with self._lock:
            self.health_metrics['total_requests'] += 1
            if success:
                self.health_metrics['successful_requests'] += 1
                self.health_metrics['response_times'].append(response_time)
                # Храним только последние 1000 замеров
                if len(self.health_metrics['response_times']) > 1000:
                    self.health_metrics['response_times'].pop(0)
                # Обновляем среднее время ответа
                self.health_metrics['avg_response_time'] = (
                    sum(self.health_metrics['response_times']) / 
                    len(self.health_metrics['response_times'])
                )
            else:
                self.health_metrics['failed_requests'] += 1
                self.health_metrics['last_error'] = str(error)
                self.health_metrics['last_error_time'] = time.time()
    
    def can_restart(self) -> bool:
        """Проверяет, можно ли перезапустить сервис"""
        now = time.time()
        # Удаляем старые записи о перезапусках
        self.restart_times = [t for t in self.restart_times if now - t < self.restart_window]
        return len(self.restart_times) < self.max_restarts
    
    def record_restart(self):
        """Записывает факт перезапуска"""
        self.restart_times.append(time.time())
    
    def get_status(self) -> Dict[str, Any]:
        """Возвращает текущее состояние сервиса"""
        uptime = time.time() - self.health_metrics['start_time']
        return {
            'service': self.service_name,
            'status': 'running',
            'uptime_seconds': uptime,
            'uptime_human': str(timedelta(seconds=int(uptime))),
            'total_requests': self.health_metrics['total_requests'],
            'success_rate': (
                self.health_metrics['successful_requests'] / self.health_metrics['total_requests'] * 100
                if self.health_metrics['total_requests'] > 0 else 100
            ),
            'avg_response_time': self.health_metrics['avg_response_time'],
            'last_error': self.health_metrics['last_error'],
            'last_error_time': (
                datetime.fromtimestamp(self.health_metrics['last_error_time']).isoformat()
                if self.health_metrics['last_error_time'] else None
            ),
            'restarts_in_last_hour': len([t for t in self.restart_times if time.time() - t < 3600]),
            'total_restarts': len(self.restart_times)
        }


class SelfHealingSystem:
    """Система самовосстановления и мониторинга"""
    
    def __init__(self, service_name: str, max_restarts: int = 3, restart_window: int = 3600):
        self.service_name = service_name
        self.health = ServiceHealth(service_name, max_restarts, restart_window)
        self.monitoring_interval = 60  # секунды
        self._monitoring = False
        self._monitor_thread = None
        self._cleanup_handlers = []
        self._start_time = time.time()
        self._shutdown_event = threading.Event()
        
        # Регистрируем обработчики завершения
        self._register_signal_handlers()
    
    def _register_signal_handlers(self):
        """Регистрирует обработчики сигналов для корректного завершения"""
        signals = [signal.SIGINT, signal.SIGTERM]
        if platform.system() != 'Windows':
            signals.append(signal.SIGHUP)
        
        for sig in signals:
            try:
                signal.signal(sig, self._handle_shutdown_signal)
            except (ValueError, AttributeError) as e:
                logger.warning(f"Не удалось зарегистрировать обработчик для {sig}: {e}")
    
    def _handle_shutdown_signal(self, signum, frame):
        """Обработчик сигналов завершения"""
        logger.info(f"Получен сигнал {signal.Signals(signum).name}. Завершаем работу...")
        self.stop()
    
    def add_cleanup_handler(self, handler: Callable):
        """Добавляет обработчик очистки ресурсов при завершении"""
        self._cleanup_handlers.append(handler)
    
    def start_monitoring(self):
        """Запускает фоновый мониторинг сервиса"""
        if self._monitoring:
            logger.warning("Мониторинг уже запущен")
            return
            
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name=f"{self.service_name}-monitor",
            daemon=True
        )
        self._monitor_thread.start()
        logger.info("Мониторинг сервиса запущен")
    
    def _monitor_loop(self):
        """Цикл мониторинга состояния сервиса"""
        while not self._shutdown_event.is_set():
            try:
                self.check_system_resources()
                self.check_service_health()
                
                # Сохраняем состояние для отладки
                if int(time.time()) % 300 == 0:  # Каждые 5 минут
                    self.save_health_report()
                
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}", exc_info=True)
            
            self._shutdown_event.wait(self.monitoring_interval)
    
    def check_system_resources(self):
        """Проверяет системные ресурсы"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            if cpu_percent > 90:
                logger.warning(f"Высокая загрузка CPU: {cpu_percent}%")
                
            if mem.percent > 90:
                logger.warning(f"Высокое использование памяти: {mem.percent}%")
                
            if disk.percent > 90:
                logger.warning(f"Мало свободного места на диске: {disk.percent}%")
                
        except Exception as e:
            logger.error(f"Ошибка при проверке системных ресурсов: {e}", exc_info=True)
    
    def check_service_health(self):
        """Проверяет здоровье сервиса"""
        try:
            # Проверяем, что сервис отвечает на запросы
            # Здесь можно добавить проверку эндпоинтов или других метрик
            pass
            
        except Exception as e:
            logger.error(f"Ошибка при проверке здоровья сервиса: {e}", exc_info=True)
            
            # Если сервис не отвечает, пытаемся перезапустить
            if self.health.can_restart():
                logger.warning("Попытка самовосстановления сервиса...")
                self.restart_service()
            else:
                logger.critical("Достигнуто максимальное количество перезапусков. Требуется ручное вмешательство.")
                self.stop()
    
    def restart_service(self):
        """Перезапускает сервис"""
        logger.info("Перезапуск сервиса...")
        self.health.record_restart()
        
        try:
            # Сохраняем текущее состояние
            self.save_state()
            
            # Вызываем обработчики очистки
            for handler in self._cleanup_handlers:
                try:
                    handler()
                except Exception as e:
                    logger.error(f"Ошибка в обработчике очистки: {e}", exc_info=True)
            
            # Перезапускаем процесс
            python = sys.executable
            os.execl(python, python, *sys.argv)
            
        except Exception as e:
            logger.critical(f"Критическая ошибка при перезапуске: {e}", exc_info=True)
            sys.exit(1)
    
    def save_health_report(self, filepath: str = None):
        """Сохраняет отчёт о состоянии сервиса"""
        try:
            if filepath is None:
                logs_dir = Path("logs")
                logs_dir.mkdir(exist_ok=True)
                filepath = logs_dir / f"{self.service_name}_health_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'service': self.service_name,
                'status': self.health.get_status(),
                'system': {
                    'cpu_percent': psutil.cpu_percent(),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_usage': psutil.disk_usage('/').percent,
                    'process': {
                        'pid': os.getpid(),
                        'create_time': psutil.Process().create_time(),
                        'memory_info': dict(psutil.Process().memory_info()._asdict()),
                        'num_threads': psutil.Process().num_threads()
                    }
                }
            }
            
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Ошибка при сохранении отчёта о состоянии: {e}", exc_info=True)
    
    def save_state(self, filepath: str = None):
        """Сохраняет состояние сервиса для восстановления"""
        try:
            if filepath is None:
                state_dir = Path("state")
                state_dir.mkdir(exist_ok=True)
                filepath = state_dir / f"{self.service_name}_state.json"
            
            state = {
                'timestamp': datetime.now().isoformat(),
                'service': self.service_name,
                'health': self.health.get_status(),
                'config': {
                    # Здесь можно сохранить конфигурацию сервиса
                }
            }
            
            with open(filepath, 'w') as f:
                json.dump(state, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Ошибка при сохранении состояния: {e}", exc_info=True)
    
    def load_state(self, filepath: str) -> bool:
        """Загружает сохранённое состояние сервиса"""
        try:
            if not os.path.exists(filepath):
                logger.warning(f"Файл состояния не найден: {filepath}")
                return False
                
            with open(filepath, 'r') as f:
                state = json.load(f)
                
            # Восстанавливаем состояние
            # Здесь можно добавить логику восстановления
            
            logger.info(f"Состояние сервиса восстановлено из {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке состояния: {e}", exc_info=True)
            return False
    
    def stop(self):
        """Останавливает мониторинг и освобождает ресурсы"""
        if not self._shutdown_event.is_set():
            logger.info("Остановка системы самовосстановления...")
            self._shutdown_event.set()
            
            # Вызываем обработчики очистки
            for handler in self._cleanup_handlers:
                try:
                    handler()
                except Exception as e:
                    logger.error(f"Ошибка в обработчике очистки при остановке: {e}", exc_info=True)
            
            # Сохраняем финальный отчёт
            self.save_health_report()
            logger.info("Система самовосстановления остановлена")
    
    def __enter__(self):
        """Поддержка контекстного менеджера"""
        self.start_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Завершение работы при выходе из контекста"""
        self.stop()
        if exc_type is not None:
            logger.error("Ошибка в контексте работы сервиса", exc_info=(exc_type, exc_val, exc_tb))
        return False  # Пробрасываем исключение, если оно было


def create_service_supervisor(service_name: str, target: Callable, max_restarts: int = 3):
    """
    Создаёт супервизора для управления сервисом.
    
    Args:
        service_name: Имя сервиса
        target: Целевая функция, которую нужно запустить
        max_restarts: Максимальное количество перезапусков
        
    Returns:
        SupervisorThread: Поток-супервизор
    """
    class SupervisorThread(threading.Thread):
        def __init__(self):
            super().__init__(name=f"{service_name}-supervisor", daemon=True)
            self.target = target
            self.health = ServiceHealth(service_name, max_restarts)
            self._stop_event = threading.Event()
            self._process = None
            
        def run(self):
            while not self._stop_event.is_set() and self.health.can_restart():
                try:
                    logger.info(f"Запуск сервиса {service_name}...")
                    self._process = subprocess.Popen(
                        [sys.executable, '-c', f'import sys; from {target.__module__} import {target.__name__}; {target.__name__}()'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    # Мониторим вывод процесса
                    def log_stream(stream, logger_func):
                        for line in iter(stream.readline, ''):
                            if line.strip():
                                logger_func(line.strip())
                    
                    with ThreadPoolExecutor(max_workers=2) as executor:
                        executor.submit(log_stream, self._process.stdout, logger.info)
                        executor.submit(log_stream, self._process.stderr, logger.error)
                    
                    # Ждём завершения процесса
                    return_code = self._process.wait()
                    
                    if return_code != 0:
                        logger.error(f"Сервис {service_name} завершился с кодом {return_code}")
                        self.health.record_restart()
                        time.sleep(5)  # Пауза перед перезапуском
                    else:
                        logger.info(f"Сервис {service_name} завершил работу")
                        break
                        
                except Exception as e:
                    logger.error(f"Ошибка в супервизоре сервиса {service_name}: {e}", exc_info=True)
                    self.health.record_restart()
                    time.sleep(5)  # Пауза перед перезапуском
            
            if not self.health.can_restart():
                logger.critical(f"Достигнуто максимальное количество перезапусков сервиса {service_name}")
        
        def stop(self):
            """Останавливает сервис и супервизор"""
            self._stop_event.set()
            if self._process and self._process.poll() is None:
                logger.info(f"Завершение сервиса {service_name}...")
                try:
                    # Сначала мягкое завершение
                    self._process.terminate()
                    try:
                        self._process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        # Если процесс не завершился, принудительно останавливаем
                        self._process.kill()
                        self._process.wait()
                except Exception as e:
                    logger.error(f"Ошибка при остановке сервиса: {e}", exc_info=True)
    
    return SupervisorThread()
