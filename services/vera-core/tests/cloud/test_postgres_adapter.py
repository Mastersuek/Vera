import pytest
import psycopg2
from psycopg2.extras import RealDictCursor
from app.cloud.cloud_adapter import (
    PostgresCloudAdapter,
    CloudBackend,
    TaskStatus,
    TaskResult
)

@pytest.fixture
def postgres_config() -> Dict[str, Any]:
    """Конфигурация для PostgreSQL адаптера"""
    return {
        'host': 'postgres',
        'port': 5432,
        'database': os.getenv('POSTGRES_DB', 'vera'),
        'user': os.getenv('POSTGRES_USER', 'vera'),
        'password': os.getenv('POSTGRES_PASSWORD', 'vera'),
        'sslmode': 'disable'
    }

@pytest.fixture
def postgres_client(postgres_config: Dict[str, Any]):
    """Фикстура для PostgreSQL клиента"""
    conn = psycopg2.connect(**postgres_config)
    yield conn
    conn.close()

@pytest.mark.usefixtures("postgres_client")
class TestPostgresAdapter(BaseAdapterTest):
    """Тесты для PostgreSQL адаптера"""
    
    adapter_class = PostgresCloudAdapter
    config = postgres_config
    
    async def test_postgres_table_operations(self, adapter: PostgresCloudAdapter):
        """Тестирует операции с таблицами"""
        # Создаем тестовую таблицу
        test_table = f"test_table_{int(time.time())}"
        create_query = f"""
        CREATE TABLE {test_table} (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        await adapter.execute_query(create_query)
        
        # Проверяем вставку данных
        insert_query = f"INSERT INTO {test_table} (name) VALUES (%s)"
        await adapter.execute_query(insert_query, ('test_name',))
        
        # Проверяем выборку
        select_query = f"SELECT * FROM {test_table}"
        results = await adapter.fetch_query(select_query)
        assert len(results) == 1
        assert results[0]['name'] == 'test_name'
        
        # Удаляем таблицу
        drop_query = f"DROP TABLE {test_table}"
        await adapter.execute_query(drop_query)
    
    async def test_postgres_transactions(self, adapter: PostgresCloudAdapter):
        """Тестирует транзакции"""
        # Создаем тестовую таблицу для транзакций
        test_table = f"test_table_{int(time.time())}"
        create_query = f"""
        CREATE TABLE {test_table} (
            id SERIAL PRIMARY KEY,
            value INTEGER
        )
        """
        await adapter.execute_query(create_query)
        
        try:
            # Начинаем транзакцию
            async with adapter.transaction():
                # Вставляем данные
                insert_query = f"INSERT INTO {test_table} (value) VALUES (%s)"
                await adapter.execute_query(insert_query, (10,))
                
                # Проверяем данные
                select_query = f"SELECT * FROM {test_table}"
                results = await adapter.fetch_query(select_query)
                assert len(results) == 1
                assert results[0]['value'] == 10
                
                # Генерируем ошибку для проверки отката
                raise ValueError("Test rollback")
                
        except ValueError:
            # Проверяем, что данные откатились
            results = await adapter.fetch_query(select_query)
            assert len(results) == 0
        
        finally:
            # Удаляем таблицу
            drop_query = f"DROP TABLE {test_table}"
            await adapter.execute_query(drop_query)
    
    async def test_postgres_concurrent_operations(self, adapter: PostgresCloudAdapter):
        """Тестирует параллельные операции"""
        # Создаем тестовую таблицу
        test_table = f"test_table_{int(time.time())}"
        create_query = f"""
        CREATE TABLE {test_table} (
            id SERIAL PRIMARY KEY,
            value INTEGER
        )
        """
        await adapter.execute_query(create_query)
        
        # Создаем задачи для параллельного вставления
        tasks = []
        for i in range(10):
            insert_query = f"INSERT INTO {test_table} (value) VALUES (%s)"
            task = adapter.execute_query(insert_query, (i,))
            tasks.append(task)
        
        # Ждем выполнения всех задач
        await asyncio.gather(*tasks)
        
        # Проверяем результат
        select_query = f"SELECT COUNT(*) FROM {test_table}"
        result = await adapter.fetch_query(select_query)
        assert result[0]['count'] == 10
        
        # Удаляем таблицу
        drop_query = f"DROP TABLE {test_table}"
        await adapter.execute_query(drop_query)
