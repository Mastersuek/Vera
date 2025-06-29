"""
Модуль облачного адаптера для распределенных вычислений.

Поддерживает различные бэкенды для распределенных вычислений:
- Dask (локальный и облачный)
- Ray (локальный и облачный)
- Пользовательские бэкенды
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, TypeVar, Generic
from enum import Enum
import logging
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Настройка логирования
logger = logging.getLogger(__name__)

# Тип для дженериков
T = TypeVar('T')
R = TypeVar('R')

class CloudBackend(str, Enum):
    """Поддерживаемые бэкенды для распределенных вычислений"""
    DASK = "dask"
    RAY = "ray"
    CUSTOM = "custom"

class TaskStatus(str, Enum):
    """Статусы выполнения задачи"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class TaskResult(Generic[R]):
    """Результат выполнения задачи"""
    task_id: str
    status: TaskStatus
    result: Optional[R] = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[float]:
        """Длительность выполнения задачи в секундах"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

class CloudAdapter(ABC):
    """
    Абстрактный базовый класс для облачного адаптера.
    
    Определяет общий интерфейс для работы с различными бэкендами
    распределенных вычислений.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация облачного адаптера.
        
        Args:
            config: Конфигурация адаптера
        """
        self.config = config
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """Инициализация подключения к облачному сервису"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Корректное завершение работы с облачным сервисом"""
        pass
    
    @abstractmethod
    async def submit_task(
        self, 
        func: Callable[..., R], 
        *args: Any, 
        **kwargs: Any
    ) -> str:
        """
        Отправка задачи на выполнение.
        
        Args:
            func: Функция для выполнения
            *args: Позиционные аргументы функции
            **kwargs: Именованные аргументы функции
            
        Returns:
            str: Идентификатор задачи
        """
        pass
    
    @abstractmethod
    async def get_task_result(self, task_id: str) -> TaskResult[R]:
        """
        Получение результата выполнения задачи.
        
        Args:
            task_id: Идентификатор задачи
            
        Returns:
            TaskResult: Результат выполнения задачи
        """
        pass
    
    @abstractmethod
    async def cancel_task(self, task_id: str) -> bool:
        """
        Отмена выполнения задачи.
        
        Args:
            task_id: Идентификатор задачи
            
        Returns:
            bool: True, если отмена прошла успешно
        """
        pass
    
    @abstractmethod
    async def get_task_status(self, task_id: str) -> TaskStatus:
        """
        Получение статуса задачи.
        
        Args:
            task_id: Идентификатор задачи
            
        Returns:
            TaskStatus: Текущий статус задачи
        """
        pass
    
    async def batch_submit(
        self, 
        func: Callable[..., R], 
        args_list: List[tuple], 
        **kwargs
    ) -> List[str]:
        """
        Пакетная отправка задач.
        
        Args:
            func: Функция для выполнения
            args_list: Список кортежей с аргументами для каждой задачи
            **kwargs: Общие именованные аргументы для всех задач
            
        Returns:
            List[str]: Список идентификаторов задач
        """
        task_ids = []
        for args in args_list:
            task_id = await self.submit_task(func, *args, **kwargs)
            task_ids.append(task_id)
        return task_ids
    
    async def wait_all(
        self, 
        task_ids: List[str], 
        poll_interval: float = 1.0,
        timeout: Optional[float] = None
    ) -> List[TaskResult[R]]:
        """
        Ожидание завершения всех задач.
        
        Args:
            task_ids: Список идентификаторов задач
            poll_interval: Интервал опроса статуса в секундах
            timeout: Таймаут ожидания в секундах
            
        Returns:
            List[TaskResult]: Список результатов выполнения задач
        """
        start_time = time.time()
        remaining_tasks = set(task_ids)
        results: Dict[str, TaskResult[R]] = {}
        
        while remaining_tasks:
            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError("Превышено время ожидания выполнения задач")
                
            for task_id in list(remaining_tasks):
                result = await self.get_task_result(task_id)
                if result.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                    results[task_id] = result
                    remaining_tasks.remove(task_id)
            
            if remaining_tasks:
                await asyncio.sleep(poll_interval)
        
        return [results[task_id] for task_id in task_ids]


class DaskCloudAdapter(CloudAdapter):
    """Реализация облачного адаптера для Dask"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация Dask адаптера.
        
        Args:
            config: Конфигурация Dask
                - scheduler_address: Адрес планировщика Dask (опционально)
                - local: Запускать локальный кластер (по умолчанию: True)
                - n_workers: Количество воркеров (по умолчанию: количество ядер CPU)
                - threads_per_worker: Количество потоков на воркер (по умолчанию: 1)
        """
        super().__init__(config)
        self.client = None
        self.local_cluster = None
    
    async def initialize(self) -> None:
        """Инициализация Dask клиента"""
        try:
            import dask.distributed as dd
            
            if self.config.get('local', True):
                # Создаем локальный кластер
                from dask.distributed import LocalCluster
                self.local_cluster = LocalCluster(
                    n_workers=self.config.get('n_workers'),
                    threads_per_worker=self.config.get('threads_per_worker', 1),
                    **self.config.get('cluster_kwargs', {})
                )
                self.client = dd.Client(self.local_cluster)
                logger.info(f"Запущен локальный Dask кластер: {self.client.dashboard_link}")
            else:
                # Подключаемся к существующему кластеру
                self.client = dd.Client(self.config['scheduler_address'])
                logger.info(f"Подключено к Dask кластеру: {self.client.scheduler_info()}")
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Ошибка инициализации Dask: {str(e)}")
            raise
    
    async def shutdown(self) -> None:
        """Завершение работы с Dask"""
        if self.client:
            await self.client.close()
            self.client = None
        
        if self.local_cluster:
            await self.local_cluster.close()
            self.local_cluster = None
        
        self._initialized = False
    
    async def submit_task(
        self, 
        func: Callable[..., R], 
        *args: Any, 
        **kwargs: Any
    ) -> str:
        """Отправка задачи в Dask"""
        if not self._initialized:
            await self.initialize()
        
        future = self.client.submit(func, *args, **kwargs)
        return str(future.key)
    
    async def get_task_result(self, task_id: str) -> TaskResult[R]:
        """Получение результата выполнения задачи"""
        if not self._initialized:
            raise RuntimeError("Адаптер не инициализирован")
        
        future = self.client.get_task_status(task_id)
        result = TaskResult(task_id=task_id, status=TaskStatus.PENDING)
        
        try:
            if future.status == 'pending':
                result.status = TaskStatus.PENDING
            elif future.status == 'running':
                result.status = TaskStatus.RUNNING
            elif future.status == 'finished':
                result.status = TaskStatus.COMPLETED
                result.result = future.result()
                result.end_time = time.time()
            elif future.status == 'error':
                result.status = TaskStatus.FAILED
                result.error = str(future.exception())
                result.end_time = time.time()
            elif future.status == 'cancelled':
                result.status = TaskStatus.CANCELLED
                result.end_time = time.time()
                
        except Exception as e:
            result.status = TaskStatus.FAILED
            result.error = str(e)
            result.end_time = time.time()
        
        return result
    
    async def cancel_task(self, task_id: str) -> bool:
        """Отмена выполнения задачи"""
        if not self._initialized:
            raise RuntimeError("Адаптер не инициализирован")
        
        try:
            future = self.client.get_task_status(task_id)
            cancelled = self.client.cancel(future)
            return cancelled
        except Exception as e:
            logger.error(f"Ошибка при отмене задачи {task_id}: {str(e)}")
            return False
    
    async def get_task_status(self, task_id: str) -> TaskStatus:
        """Получение статуса задачи"""
        result = await self.get_task_result(task_id)
        return result.status


class CloudAdapterFactory:
    """Фабрика для создания облачных адаптеров"""
    
    @staticmethod
    def create_adapter(
        backend_type: CloudBackend,
        config: Optional[Dict[str, Any]] = None
    ) -> CloudAdapter:
        """
        Создание экземпляра облачного адаптера.
        
        Args:
            backend_type: Тип бэкенда
            config: Конфигурация адаптера
            
        Returns:
            CloudAdapter: Экземпляр облачного адаптера
            
        Raises:
            ValueError: Если указан неподдерживаемый тип бэкенда
        """
        config = config or {}
        
        if backend_type == CloudBackend.DASK:
            return DaskCloudAdapter(config)
        elif backend_type == CloudBackend.RAY:
            # Импортируем только при необходимости
            from .ray_adapter import RayCloudAdapter
            return RayCloudAdapter(config)
        elif backend_type == CloudBackend.CUSTOM:
            # Пользовательский адаптер должен быть зарегистрирован заранее
            if 'adapter_class' not in config:
                raise ValueError("Для пользовательского адаптера необходимо указать adapter_class")
            return config['adapter_class'](config)
        else:
            raise ValueError(f"Неподдерживаемый тип бэкенда: {backend_type}")


# Пример использования
async def example_usage():
    """Пример использования облачного адаптера"""
    # Конфигурация
    config = {
        'local': True,
        'n_workers': 2,
        'threads_per_worker': 2
    }
    
    # Создаем адаптер
    adapter = CloudAdapterFactory.create_adapter(CloudBackend.DASK, config)
    
    try:
        # Инициализируем подключение
        await adapter.initialize()
        
        # Определяем функцию для выполнения
        def process_data(x: int) -> int:
            import time
            time.sleep(1)  # Имитация долгой операции
            return x * x
        
        # Отправляем задачи
        task_ids = await adapter.batch_submit(
            process_data,
            [(i,) for i in range(5)]
        )
        
        print(f"Отправлено задач: {len(task_ids)}")
        
        # Ожидаем завершения всех задач
        results = await adapter.wait_all(task_ids)
        
        # Выводим результаты
        for result in results:
            if result.status == TaskStatus.COMPLETED:
                print(f"Задача {result.task_id} завершена: {result.result}")
            else:
                print(f"Задача {result.task_id} не удалась: {result.error}")
    
    finally:
        # Завершаем работу
        await adapter.shutdown()


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
