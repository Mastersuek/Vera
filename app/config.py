import os
from pydantic import BaseSettings, Field, PostgresDsn, validator
from typing import Optional, Dict, Any
from pathlib import Path

class Settings(BaseSettings):
    """
    Настройки приложения.
    
    Параметры могут быть переопределены через переменные окружения.
    Имена переменных окружения формируются как APP_<имя_параметра>.
    Например: APP_DEBUG=true
    """
    
    # Основные настройки
    DEBUG: bool = Field(False, env='DEBUG')
    APP_NAME: str = "Vera Platform"
    VERSION: str = "1.0.0"
    SECRET_KEY: str = Field(..., env='SECRET_KEY')
    
    # Настройки API
    API_PREFIX: str = "/api"
    API_V1_STR: str = "/api/v1"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 дней
    
    # Настройки CORS
    BACKEND_CORS_ORIGINS: list[str] = ["*"]
    
    # Настройки базы данных
    POSTGRES_SERVER: str = Field(..., env='POSTGRES_SERVER')
    POSTGRES_USER: str = Field(..., env='POSTGRES_USER')
    POSTGRES_PASSWORD: str = Field(..., env='POSTGRES_PASSWORD')
    POSTGRES_DB: str = Field(..., env='POSTGRES_DB')
    SQLALCHEMY_DATABASE_URI: Optional[PostgresDsn] = None
    
    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        """
        Формирует строку подключения к базе данных.
        
        Args:
            v: Текущее значение (если есть)
            values: Значения других полей настроек
            
        Returns:
            str: Строка подключения к PostgreSQL
        """
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql",
            user=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_SERVER"),
            path=f"/{values.get('POSTGRES_DB') or ''}",
        )
    
    # Настройки Redis
    REDIS_HOST: str = Field("redis", env='REDIS_HOST')
    REDIS_PORT: int = Field(6379, env='REDIS_PORT')
    REDIS_DB: int = 0
    
    # Настройки JWT
    JWT_SECRET_KEY: str = Field(..., env='JWT_SECRET_KEY')
    JWT_ALGORITHM: str = "HS256"
    
    # Настройки загрузки файлов
    UPLOAD_FOLDER: str = str(Path(__file__).parent / "uploads")
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16 MB
    ALLOWED_EXTENSIONS: set[str] = {"txt", "pdf", "png", "jpg", "jpeg", "gif"}
    
    # Настройки логирования
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = 'utf-8'

# Создаем экземпляр настроек
settings = Settings()

# Создаем директорию для загрузок, если она не существует
os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
