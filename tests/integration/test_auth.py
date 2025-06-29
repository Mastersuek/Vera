import pytest
from .test_config import test_config
import requests
from datetime import datetime
import jwt
import hashlib
import secrets

# Конфигурация для тестов
@pytest.fixture(scope="module")
def auth_config():
    return test_config()

# Генерация тестовых данных
@pytest.fixture
async def test_user():
    return {
        "username": f"test_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}@test.com",
        "password": "SecurePassword123!",
        "role": "test_role",
        "permissions": ["read", "write"]
    }

# Тесты аутентификации
class TestAuthentication:
    @pytest.mark.asyncio
    async def test_user_registration(self, auth_config, test_user):
        """Тест регистрации пользователя"""
        response = requests.post(
            f"{auth_config['service_url']}/api/v1/register",
            json=test_user
        )
        assert response.status_code == 201
        assert "access_token" in response.json()
        
    @pytest.mark.asyncio
    async def test_login(self, auth_config, test_user):
        """Тест входа в систему"""
        login_data = {
            "username": test_user["username"],
            "password": test_user["password"]
        }
        response = requests.post(
            f"{auth_config['service_url']}/api/v1/login",
            json=login_data
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
        
    @pytest.mark.asyncio
    async def test_password_hashing(self, auth_config, test_user):
        """Тест хеширования пароля"""
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            test_user["password"].encode(),
            salt.encode(),
            auth_config["security"]["password_salt_rounds"]
        )
        assert len(hashed) > 0
        
    @pytest.mark.asyncio
    async def test_token_validation(self, auth_config, test_user):
        """Тест валидации JWT токена"""
        token = jwt.encode(
            {
                "sub": test_user["username"],
                "exp": datetime.utcnow() + timedelta(minutes=30),
                "role": test_user["role"],
                "permissions": test_user["permissions"]
            },
            auth_config["security"]["jwt_secret"],
            algorithm="HS256"
        )
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{auth_config['service_url']}/api/v1/protected",
            headers=headers
        )
        assert response.status_code == 200

# Тесты авторизации
class TestAuthorization:
    @pytest.mark.asyncio
    async def test_role_based_access(self, auth_config, test_user):
        """Тест ролевого доступа"""
        # Создаем пользователя с ограниченными правами
        limited_user = test_user.copy()
        limited_user["permissions"] = ["read"]
        
        # Регистрируем пользователя
        response = requests.post(
            f"{auth_config['service_url']}/api/v1/register",
            json=limited_user
        )
        assert response.status_code == 201
        
        # Пытаемся получить доступ к защищенному ресурсу
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Доступ к ресурсу с правом "write" должен быть запрещен
        response = requests.post(
            f"{auth_config['service_url']}/api/v1/write",
            headers=headers
        )
        assert response.status_code == 403  # Forbidden
        
    @pytest.mark.asyncio
    async def test_resource_based_access(self, auth_config, test_user):
        """Тест доступа к ресурсам"""
        # Создаем пользователя с доступом к конкретному ресурсу
        resource_user = test_user.copy()
        resource_user["permissions"] = ["access:sensitive_data"]
        
        # Регистрируем пользователя
        response = requests.post(
            f"{auth_config['service_url']}/api/v1/register",
            json=resource_user
        )
        assert response.status_code == 201
        
        # Проверяем доступ к ресурсу
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Доступ к ресурсу разрешен
        response = requests.get(
            f"{auth_config['service_url']}/api/v1/sensitive_data",
            headers=headers
        )
        assert response.status_code == 200
