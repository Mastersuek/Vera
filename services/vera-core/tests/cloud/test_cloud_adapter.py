"""
Модуль тестирования облачного адаптера.

Содержит тесты для проверки работы облачного адаптера
с различными бэкендами распределенных вычислений.
"""

import asyncio
import pytest
import time
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

from app.cloud.cloud_adapter import (
    CloudAdapter,
    DaskCloudAdapter,
    CloudBackend,
    CloudAdapterFactory,
    TaskStatus,
    TaskResult
)

# Фикстура для event loop
@pytest.fixture
def event_loop():
    """Создаем event loop для тестов"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# Фикстура для конфигурации
@pytest.fixture
def dask_config() -> Dict[str, Any]:
    """Конфигурация для Dask адаптера"""
    return {
        'local': True,
        'n_workers': 2,
        'threads_per_worker': 1
    }

# Фикстура для Dask адаптера
@pytest.fixture
async def dask_adapter(dask_config: Dict[str, Any]) -> DaskCloudAdapter:
    """Создаем и инициализируем Dask адаптер"""
    adapter = DaskCloudAdapter(dask_config)
    await adapter.initialize()
    yield adapter
    await adapter.shutdown()

# Тест фабрики адаптеров
def test_adapter_factory(dask_config: Dict[str, Any]):
    """Тестируем создание адаптера через фабрику"""
    # Тестируем создание Dask адаптера
    dask_adapter = CloudAdapterFactory.create_adapter(CloudBackend.DASK, dask_config)
    assert isinstance(dask_adapter, DaskCloudAdapter)
    assert dask_adapter.config == dask_config
    
    # Тестируем обработку неизвестного бэкенда
    with pytest.raises(ValueError, match="Неподдерживаемый тип бэкенда"):
        CloudAdapterFactory.create_adapter("unknown_backend")  # type: ignore

# Тест инициализации и завершения работы
@pytest.mark.asyncio
async def test_dask_adapter_lifecycle(dask_config: Dict[str, Any]):
    """Тестируем жизненный цикл Dask адаптера"""
    adapter = DaskCloudAdapter(dask_config)
    
    # Проверяем, что адаптер не инициализирован
    assert not hasattr(adapter, '_initialized') or not adapter._initialized
    
    # Инициализируем
    await adapter.initialize()
    assert adapter._initialized
    assert adapter.client is not None
    
    # Завершаем работу
    await adapter.shutdown()
    assert not hasattr(adapter, '_initialized') or not adapter._initialized
    assert not hasattr(adapter, 'client') or adapter.client is None

# Тест отправки и выполнения задачи
@pytest.mark.asyncio
async def test_submit_and_get_result(dask_adapter: DaskCloudAdapter):
    """Тестируем отправку задачи и получение результата"""
    # Определяем тестовую функцию
    def test_func(x: int) -> int:
        return x * 2
    
    # Отправляем задачу
    task_id = await dask_adapter.submit_task(test_func, 5)
    assert task_id is not None
    
    # Получаем результат
    result = await dask_adapter.get_task_result(task_id)
    
    # Проверяем результат
    assert result.status == TaskStatus.COMPLETED
    assert result.result == 10
    assert result.error is None
    assert result.duration is not None

# Тест пакетной отправки задач
@pytest.mark.asyncio
async def test_batch_submit(dask_adapter: DaskCloudAdapter):
    """Тестируем пакетную отправку задач"""
    # Определяем тестовую функцию
    def test_func(x: int, y: int) -> int:
        return x * y
    
    # Подготавливаем аргументы для пакетной отправки
    args_list = [(i, i+1) for i in range(5)]
    
    # Отправляем пакет задач
    task_ids = await dask_adapter.batch_submit(test_func, args_list)
    
    # Проверяем, что все задачи отправлены
    assert len(task_ids) == len(args_list)
    
    # Ожидаем завершения всех задач
    results = await dask_adapter.wait_all(task_ids)
    
    # Проверяем результаты
    for i, result in enumerate(results):
        assert result.status == TaskStatus.COMPLETED
        assert result.result == i * (i + 1)

# Тест отмены задачи
@pytest.mark.asyncio
async def test_cancel_task(dask_adapter: DaskCloudAdapter):
    """Тестируем отмену выполнения задачи"""
    # Определяем долгую тестовую функцию
    def long_running_func() -> int:
        import time
        time.sleep(10)  # Долгая операция
        return 42
    
    # Отправляем задачу
    task_id = await dask_adapter.submit_task(long_running_func)
    
    # Пытаемся отменить задачу
    cancelled = await dask_adapter.cancel_task(task_id)
    
    # Проверяем, что задача отменена или завершена
    # (в зависимости от того, как быстро успела запуститься)
    status = await dask_adapter.get_task_status(task_id)
    assert status in (TaskStatus.CANCELLED, TaskStatus.COMPLETED)

# Тест обработки ошибок
@pytest.mark.asyncio
async def test_error_handling(dask_adapter: DaskCloudAdapter):
    """Тестируем обработку ошибок при выполнении задачи"""
    # Определяем функцию, которая вызывает исключение
    def failing_func() -> int:
        raise ValueError("Тестовая ошибка")
    
    # Отправляем задачу
    task_id = await dask_adapter.submit_task(failing_func)
    
    # Получаем результат
    result = await dask_adapter.get_task_result(task_id)
    
    # Проверяем, что задача завершилась с ошибкой
    assert result.status == TaskStatus.FAILED
    assert "Тестовая ошибка" in str(result.error)

# Тест таймаута при ожидании задач
@pytest.mark.asyncio
async def test_wait_all_timeout(dask_adapter: DaskCloudAdapter):
    """Тестируем таймаут при ожидании завершения задач"""
    # Определяем долгую тестовую функцию
    def long_running_func() -> int:
        import time
        time.sleep(5)  # Долгая операция
        return 42
    
    # Отправляем задачу
    task_id = await dask_adapter.submit_task(long_running_func)
    
    # Пытаемся дождаться с маленьким таймаутом
    with pytest.raises(TimeoutError, match="Превышено время ожидания"):
        await dask_adapter.wait_all([task_id], timeout=0.1)

# Тест параллельного выполнения задач
@pytest.mark.asyncio
async def test_parallel_execution(dask_adapter: DaskCloudAdapter):
    """Тестируем параллельное выполнение задач"""
    # Счетчик для проверки параллельного выполнения
    execution_counter = 0
    counter_lock = asyncio.Lock()
    
    # Определяем тестовую функцию
    async def parallel_func(idx: int) -> int:
        nonlocal execution_counter
        # Имитируем работу
        await asyncio.sleep(1)
        
        # Обновляем счетчик
        async with counter_lock:
            execution_counter += 1
        
        return idx * 2
    
    # Отправляем несколько задач
    task_ids = [
        await dask_adapter.submit_task(parallel_func, i)
        for i in range(5)
    ]
    
    # Засекаем время выполнения
    start_time = time.time()
    
    # Ожидаем завершения всех задач
    await dask_adapter.wait_all(task_ids)
    
    # Проверяем, что задачи выполнялись параллельно
    # (общее время должно быть значительно меньше, чем 5 секунд)
    execution_time = time.time() - start_time
    assert execution_time < 3.0  # С запасом на накладные расходы
    
    # Проверяем, что все задачи были выполнены
    assert execution_counter == 5

# Тест с моком для Dask клиента
@pytest.mark.asyncio
async def test_dask_adapter_with_mock():
    """Тестируем Dask адаптер с моком клиента"""
    # Создаем мок клиента
    mock_client = MagicMock()
    mock_future = MagicMock()
    
    # Настраиваем мок
    mock_client.submit.return_value = mock_future
    mock_future.key = "test_task_123"
    mock_future.status = 'finished'
    mock_future.result.return_value = 42
    
    # Создаем адаптер с моком
    with patch('dask.distributed.Client', return_value=mock_client):
        adapter = DaskCloudAdapter({'local': True})
        await adapter.initialize()
        
        try:
            # Отправляем задачу
            task_id = await adapter.submit_task(lambda x: x * 2, 21)
            assert task_id == "test_task_123"
            
            # Получаем результат
            result = await adapter.get_task_result(task_id)
            assert result.status == TaskStatus.COMPLETED
            assert result.result == 42
            
        finally:
            await adapter.shutdown()

# Тест с пользовательским адаптером
@pytest.mark.asyncio
async def test_custom_adapter():
    """Тестируем создание пользовательского адаптера"""
    # Создаем пользовательский адаптер
    class CustomAdapter(CloudAdapter):
        async def initialize(self):
            self._initialized = True
            
        async def shutdown(self):
            self._initialized = False
            
        async def submit_task(self, func, *args, **kwargs):
            return "custom_task_123"
            
        async def get_task_result(self, task_id):
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                result=42
            )
            
        async def cancel_task(self, task_id):
            return True
            
        async def get_task_status(self, task_id):
            return TaskStatus.COMPLETED
    
    # Регистрируем пользовательский адаптер
    config = {
        'adapter_class': CustomAdapter,
        'custom_param': 'value'
    }
    
    # Создаем через фабрику
    adapter = CloudAdapterFactory.create_adapter(CloudBackend.CUSTOM, config)
    assert isinstance(adapter, CustomAdapter)
    
    # Проверяем работу адаптера
    await adapter.initialize()
    try:
        task_id = await adapter.submit_task(lambda x: x * 2, 21)
        assert task_id == "custom_task_123"
        
        result = await adapter.get_task_result(task_id)
        assert result.status == TaskStatus.COMPLETED
        assert result.result == 42
        
    finally:
        await adapter.shutdown()
