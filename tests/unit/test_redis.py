import pytest
from .base_test import BaseTest
import redis

@pytest.mark.redis
@pytest.mark.unit
class TestRedis(BaseTest):
    def setup(self):
        super().setup()
        self.log_step("Connecting to Redis")
        try:
            self.redis = redis.Redis(
                host='redis',
                port=6379,
                password=os.getenv('REDIS_PASSWORD')
            )
            self.redis.ping()
            self.log_step("Successfully connected to Redis")
        except Exception as e:
            self.log_error(f"Failed to connect to Redis: {str(e)}")
            pytest.fail(f"Failed to connect to Redis: {str(e)}")

    def test_redis_connection(self):
        """Тест подключения к Redis"""
        self.log_step("Testing Redis connection")
        try:
            self.assert_with_log(self.redis.ping(), "Redis connection is alive")
        except Exception as e:
            self.log_error(f"Redis connection test failed: {str(e)}")
            pytest.fail(f"Redis connection test failed: {str(e)}")

    def test_redis_basic_operations(self):
        """Тест базовых операций Redis"""
        self.log_step("Testing Redis basic operations")
        test_key = f"test_key_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        test_value = "test_value"
        
        try:
            # Установка значения
            self.redis.set(test_key, test_value)
            self.assert_with_log(
                self.redis.get(test_key) == test_value.encode(),
                f"Value for key {test_key} was set correctly"
            )
            
            # Удаление значения
            self.redis.delete(test_key)
            self.assert_with_log(
                self.redis.get(test_key) is None,
                f"Key {test_key} was successfully deleted"
            )
            
        except Exception as e:
            self.log_error(f"Redis operations test failed: {str(e)}")
            pytest.fail(f"Redis operations test failed: {str(e)}")
