"""
Модуль конфигурации для агента управления моделями ИИ.

Содержит настройки по умолчанию и загружает переменные окружения.
"""
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    """Настройки приложения.
    
    Параметры могут быть переопределены через переменные окружения.
    """
    
    # Основные настройки
    DEBUG: bool = Field(False, env="DEBUG")
    APP_NAME: str = "Vera AI Agent"
    VERSION: str = "1.0.0"
    
    # Настройки API
    API_PREFIX: str = "/api"
    API_V1_STR: str = "/api/v1"
    
    # Настройки Redis
    REDIS_HOST: str = Field("redis", env="REDIS_HOST")
    REDIS_PORT: int = Field(6379, env="REDIS_PORT")
    REDIS_PASSWORD: str = Field("", env="REDIS_PASSWORD")
    REDIS_DB: int = Field(0, env="REDIS_DB")
    
    # Настройки моделей
    MODEL_CACHE_DIR: str = Field(
        str(Path.home() / ".cache" / "vera" / "models"),
        env="MODEL_CACHE_DIR"
    )
    
    # Список моделей по умолчанию для загрузки
    DEFAULT_MODELS: List[str] = [
        "sentence-transformers/all-mpnet-base-v2",
        "facebook/bart-large-mnli",
        "bigscience/bloom-560m",
    ]
    
    # Настройки очереди задач
    RQ_QUEUE_NAME: str = "default"
    RQ_WORKER_COUNT: int = 2
    
    # Настройки логирования
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = 'utf-8'
    
    @validator('MODEL_CACHE_DIR')
    def validate_model_cache_dir(cls, v):
        """Проверяет и создает директорию для кэша моделей, если она не существует."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path.absolute())


# Создаем экземпляр настроек
settings = Settings()

# Создаем директорию для кэша моделей, если её нет
os.makedirs(settings.MODEL_CACHE_DIR, exist_ok=True)
