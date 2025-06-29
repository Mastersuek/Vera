import pytest
from typing import Any, Dict, Type
from app.cloud.cloud_adapter import (
    CloudAdapter,
    CloudBackend,
    TaskStatus,
    TaskResult
)

class BaseAdapterTest:
    """Базовый класс для тестирования адаптеров"""
    
    adapter_class: Type[CloudAdapter]
    config: Dict[str, Any]
    
    @pytest.fixture
    async def adapter(self) -> CloudAdapter:
        """Создает и инициализирует адаптер"""
        adapter = self.adapter_class(self.config)
        await adapter.initialize()
        yield adapter
        await adapter.shutdown()
    
    async def test_adapter_lifecycle(self, adapter: CloudAdapter):
        """Тестирует жизненный цикл адаптера"""
        assert adapter._initialized
        assert adapter.client is not None
        
        await adapter.shutdown()
        assert not adapter._initialized
        assert adapter.client is None
    
    async def test_submit_and_get_result(self, adapter: CloudAdapter):
        """Тестирует отправку задачи и получение результата"""
        # Определяем тестовую функцию
        def test_func(x: int) -> int:
            return x * 2
        
        # Отправляем задачу
        task_id = await adapter.submit_task(test_func, 5)
        assert task_id is not None
        
        # Получаем результат
        result = await adapter.get_task_result(task_id)
        
        # Проверяем результат
        assert result.status == TaskStatus.COMPLETED
        assert result.result == 10
        assert result.error is None
        assert result.duration is not None
    
    async def test_task_status_updates(self, adapter: CloudAdapter):
        """Тестирует обновления статуса задачи"""
        # Определяем тестовую функцию с задержкой
        def test_func(x: int) -> int:
            time.sleep(1)
            return x * 2
        
        # Отправляем задачу
        task_id = await adapter.submit_task(test_func, 5)
        
        # Проверяем статус в процессе выполнения
        status = await adapter.get_task_status(task_id)
        assert status in [TaskStatus.PENDING, TaskStatus.RUNNING]
        
        # Ждем завершения и проверяем финальный статус
        await asyncio.sleep(2)
        status = await adapter.get_task_status(task_id)
        assert status == TaskStatus.COMPLETED
    
    async def test_task_error_handling(self, adapter: CloudAdapter):
        """Тестирует обработку ошибок в задачах"""
        # Определяем функцию, которая выбрасывает ошибку
        def error_func() -> None:
            raise ValueError("Test error")
        
        # Отправляем задачу
        task_id = await adapter.submit_task(error_func)
        
        # Ждем завершения и проверяем результат
        await asyncio.sleep(2)
        result = await adapter.get_task_result(task_id)
        
        assert result.status == TaskStatus.FAILED
        assert result.error is not None
        assert "Test error" in str(result.error)
    
    async def test_multiple_tasks(self, adapter: CloudAdapter):
        """Тестирует выполнение множества задач"""
        # Определяем тестовую функцию
        def test_func(x: int) -> int:
            return x * 2
        
        # Отправляем несколько задач
        task_ids = []
        for i in range(5):
            task_id = await adapter.submit_task(test_func, i)
            task_ids.append(task_id)
        
        # Ждем завершения всех задач
        await asyncio.sleep(2)
        
        # Проверяем результаты
        for i, task_id in enumerate(task_ids):
            result = await adapter.get_task_result(task_id)
            assert result.status == TaskStatus.COMPLETED
            assert result.result == i * 2
            assert result.error is None
