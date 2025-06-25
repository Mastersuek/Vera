"""
Конфигурация интеграции с MCP (Microservice Control Plane) GitHub.

Этот модуль предоставляет настройки и утилиты для работы с GitHub API
в качестве контроллера распределенных задач.
"""

import os
from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl, validator
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


class GitHubEnvironment(str, Enum):
    """Доступные окружения GitHub."""
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"


class GitHubAppAuth(BaseModel):
    """Настройки аутентификации GitHub App."""
    app_id: str = Field(..., description="GitHub App ID")
    private_key: str = Field(..., description="Содержимое приватного ключа")
    installation_id: str = Field(..., description="ID установки приложения")
    webhook_secret: str = Field(..., description="Секрет для вебхуков")

    class Config:
        env_prefix = "GITHUB_APP_"
        env_file = ".env"
        env_file_encoding = "utf-8"

    @validator('private_key', pre=True)
    def load_private_key(cls, v: str) -> str:
        """Загружает приватный ключ из файла, если передан путь."""
        if v and v.endswith(('.pem', '.key')):
            try:
                with open(v, 'r') as f:
                    return f.read()
            except Exception as e:
                raise ValueError(f"Не удалось загрузить приватный ключ: {e}")
        return v


class GitHubRepoConfig(BaseModel):
    """Конфигурация репозитория GitHub."""
    owner: str = Field(..., description="Владелец репозитория")
    name: str = Field(..., description="Название репозитория")
    branch: str = Field("main", description="Ветка по умолчанию")
    workflows_dir: str = Field(".github/workflows", description="Директория с workflow файлами")

    @property
    def full_name(self) -> str:
        """Полное имя репозитория в формате owner/name."""
        return f"{self.owner}/{self.name}"


class MCPGitHubConfig(BaseModel):
    """Основная конфигурация MCP GitHub."""
    enabled: bool = Field(True, description="Включена ли интеграция с GitHub")
    environment: GitHubEnvironment = Field(
        GitHubEnvironment.DEVELOPMENT,
        description="Окружение (production/staging/development)"
    )
    base_url: HttpUrl = Field(
        "https://api.github.com",
        description="Базовый URL GitHub API"
    )
    auth: GitHubAppAuth = Field(..., description="Настройки аутентификации")
    repo: GitHubRepoConfig = Field(..., description="Конфигурация репозитория")
    max_retries: int = Field(3, description="Максимальное количество повторных попыток")
    timeout: int = Field(30, description="Таймаут запросов в секундах")

    class Config:
        env_prefix = "MCP_GITHUB_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        use_enum_values = True


def load_github_config(env_file: str = None) -> MCPGitHubConfig:
    """
    Загружает конфигурацию MCP GitHub из переменных окружения.
    
    Args:
        env_file: Путь к файлу .env (опционально)
        
    Returns:
        MCPGitHubConfig: Загруженная конфигурация
    """
    if env_file:
        load_dotenv(env_file)
    
    return MCPGitHubConfig(
        auth=GitHubAppAuth(),
        repo=GitHubRepoConfig(
            owner=os.getenv("GITHUB_REPO_OWNER", ""),
            name=os.getenv("GITHUB_REPO_NAME", ""),
            branch=os.getenv("GITHUB_REPO_BRANCH", "main"),
            workflows_dir=os.getenv("GITHUB_WORKFLOWS_DIR", ".github/workflows"),
        ),
        environment=os.getenv("GITHUB_ENV", GitHubEnvironment.DEVELOPMENT),
        base_url=os.getenv("GITHUB_API_URL", "https://api.github.com"),
        enabled=os.getenv("GITHUB_INTEGRATION_ENABLED", "true").lower() == "true",
    )


# Глобальный экземпляр конфигурации
config = load_github_config()


if __name__ == "__main__":
    # Пример использования
    print("Текущая конфигурация MCP GitHub:")
    print(f"- Репозиторий: {config.repo.full_name}")
    print(f"- Окружение: {config.environment}")
    print(f"- API URL: {config.base_url}")
    print(f"- Аутентификация: {'настроена' if config.auth.app_id else 'отсутствует'}")
