import pytest
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

def pytest_addoption(parser):
    parser.addoption(
        "--service",
        action="store",
        default="all",
        help="Run tests for specific service: core, dlp, proxy, auth, audit"
    )
    parser.addoption(
        "--env",
        action="store",
        default="test",
        help="Environment to run tests against: test, dev, prod"
    )

@pytest.fixture(scope="session")
def service_url(request):
    """URL сервиса для тестирования"""
    service = request.config.getoption("--service")
    env = request.config.getoption("--env")
    
    # Получаем URL из переменных окружения
    service_urls = {
        "core": os.getenv(f"VERA_CORE_URL_{env.upper()}", "http://vera-core:8000"),
        "dlp": os.getenv(f"VERA_DLP_URL_{env.upper()}", "http://vera-dlp:8001"),
        "proxy": os.getenv(f"VERA_PROXY_URL_{env.upper()}", "http://vera-proxy:8002"),
        "auth": os.getenv(f"VERA_AUTH_URL_{env.upper()}", "http://vera-auth:8003"),
        "audit": os.getenv(f"VERA_AUDIT_URL_{env.upper()}", "http://vera-audit:8004")
    }
    
    if service == "all":
        return service_urls
    return service_urls.get(service)

@pytest.fixture(scope="session")
def test_config():
    """Конфигурация для тестирования"""
    return {
        "database": {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", 5432)),
            "name": os.getenv("DB_NAME", "vera_test"),
            "user": os.getenv("DB_USER", "test_user"),
            "password": os.getenv("DB_PASSWORD", "test_password")
        },
        "redis": {
            "host": os.getenv("REDIS_HOST", "localhost"),
            "port": int(os.getenv("REDIS_PORT", 6379)),
            "password": os.getenv("REDIS_PASSWORD", "")
        },
        "security": {
            "jwt_secret": os.getenv("JWT_SECRET", "test_secret"),
            "password_salt_rounds": int(os.getenv("PASSWORD_SALT_ROUNDS", 12))
        }
    }
