import pytest
import redis
from app.cloud.cloud_adapter import (
    RedisCloudAdapter,
    CloudBackend,
    TaskStatus,
    TaskResult
)

@pytest.fixture
def redis_config() -> Dict[str, Any]:
    """Конфигурация для Redis адаптера"""
    return {
        'host': 'redis',
        'port': 6379,
        'password': os.getenv('REDIS_PASSWORD', ''),
        'db': 0
    }

@pytest.fixture
def redis_client(redis_config: Dict[str, Any]) -> redis.Redis:
    """Фикстура для Redis клиента"""
    client = redis.Redis(**redis_config)
    yield client
    client.flushdb()

@pytest.mark.usefixtures("redis_client")
class TestRedisAdapter(BaseAdapterTest):
    """Тесты для Redis адаптера"""
    
    adapter_class = RedisCloudAdapter
    config = redis_config
    
    async def test_redis_key_management(self, adapter: RedisCloudAdapter):
        """Тестирует управление ключами в Redis"""
        # Создаем тестовый ключ
        test_key = f"test_key_{int(time.time())}"
        test_value = {"data": "test_value"}
        
        # Устанавливаем значение
        await adapter.redis.set(test_key, json.dumps(test_value))
        
        # Проверяем чтение
        result = json.loads(await adapter.redis.get(test_key))
        assert result == test_value
        
        # Проверяем удаление
        await adapter.redis.delete(test_key)
        assert await adapter.redis.get(test_key) is None
    
    async def test_redis_pubsub(self, adapter: RedisCloudAdapter):
        """Тестирует публикацию и подписку в Redis"""
        # Создаем тестовый канал
        test_channel = f"test_channel_{int(time.time())}"
        
        # Создаем подписчика
        pubsub = adapter.redis.pubsub()
        await pubsub.subscribe(test_channel)
        
        # Публикуем сообщение
        test_message = {"data": "test_message"}
        await adapter.redis.publish(test_channel, json.dumps(test_message))
        
        # Ждем и проверяем сообщение
        message = await pubsub.get_message()
        assert message is not None
        assert json.loads(message['data']) == test_message
        
        # Отключаем подписчика
        await pubsub.unsubscribe()
    
    async def test_redis_ttl(self, adapter: RedisCloudAdapter):
        """Тестирует TTL для ключей"""
        # Создаем ключ с TTL
        test_key = f"test_key_{int(time.time())}"
        test_value = {"data": "test_value"}
        ttl_seconds = 2
        
        # Устанавливаем значение с TTL
        await adapter.redis.set(test_key, json.dumps(test_value), ex=ttl_seconds)
        
        # Проверяем, что ключ существует
        assert await adapter.redis.exists(test_key)
        
        # Ждем, пока ключ истечет
        await asyncio.sleep(ttl_seconds + 1)
        
        # Проверяем, что ключ удален
        assert not await adapter.redis.exists(test_key)
