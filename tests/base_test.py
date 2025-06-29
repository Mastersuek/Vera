import pytest
import logging
from datetime import datetime
from .logging_config import setup_test_logging

logger = setup_test_logging()

class BaseTest:
    @pytest.fixture(autouse=True)
    def setup(self):
        """Настройка перед каждым тестом"""
        self.test_start_time = datetime.now()
        self.test_name = self.__class__.__name__
        logger.info(f"=== Starting test {self.test_name} ===")
        
    def teardown(self):
        """Очистка после теста"""
        test_duration = datetime.now() - self.test_start_time
        logger.info(f"=== Finished test {self.test_name} in {test_duration} ===")
        
    def log_step(self, message):
        """Логирование шага теста"""
        logger.info(f"[Step] {message}")
        
    def log_error(self, message):
        """Логирование ошибки"""
        logger.error(f"[Error] {message}")
        
    def assert_with_log(self, condition, message):
        """Утверждение с логированием"""
        try:
            assert condition, message
            logger.info(f"[Assert] {message} - PASSED")
        except AssertionError as e:
            logger.error(f"[Assert] {message} - FAILED: {str(e)}")
            raise e
