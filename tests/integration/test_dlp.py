import pytest
from .test_config import test_config
import requests
import re
from datetime import datetime

# Конфигурация для тестов DLP
@pytest.fixture(scope="module")
def dlp_config():
    return test_config()

# Тестовые данные для DLP
class TestDLPSamples:
    def __init__(self):
        self.pii_data = {
            "email": "test@example.com",
            "phone": "+79001234567",
            "passport": "1234 567890",
            "address": "123 Main St, Anytown, 12345"
        }
        
        self.financial_data = {
            "card_number": "4111111111111111",
            "account": "12345678901234567890",
            "iban": "DE44500105170445126789"
        }
        
        self.medical_data = {
            "medical_record": "MRN123456",
            "diagnosis": "Diabetes Mellitus",
            "prescription": "Metformin 500mg"
        }
        
        self.corporate_data = {
            "api_key": "sk_live_1234567890abcdef1234567890abcdef",
            "secret": "my_secret_key_123456",
            "token": "access_token_123456"
        }

# Тесты DLP
class TestDLPEngine:
    @pytest.mark.asyncio
    async def test_pii_detection(self, dlp_config, test_dlp_samples):
        """Тест обнаружения персональных данных"""
        for field, value in test_dlp_samples.pii_data.items():
            response = requests.post(
                f"{dlp_config['service_url']}/api/v1/dlp/scan",
                json={"content": value}
            )
            assert response.status_code == 200
            result = response.json()
            assert result["violations"]
            assert any(violation["type"] == "PII" for violation in result["violations"])
            
    @pytest.mark.asyncio
    async def test_financial_data_detection(self, dlp_config, test_dlp_samples):
        """Тест обнаружения финансовых данных"""
        for field, value in test_dlp_samples.financial_data.items():
            response = requests.post(
                f"{dlp_config['service_url']}/api/v1/dlp/scan",
                json={"content": value}
            )
            assert response.status_code == 200
            result = response.json()
            assert result["violations"]
            assert any(violation["type"] == "FINANCIAL" for violation in result["violations"])
            
    @pytest.mark.asyncio
    async def test_medical_data_detection(self, dlp_config, test_dlp_samples):
        """Тест обнаружения медицинских данных"""
        for field, value in test_dlp_samples.medical_data.items():
            response = requests.post(
                f"{dlp_config['service_url']}/api/v1/dlp/scan",
                json={"content": value}
            )
            assert response.status_code == 200
            result = response.json()
            assert result["violations"]
            assert any(violation["type"] == "MEDICAL" for violation in result["violations"])
            
    @pytest.mark.asyncio
    async def test_corporate_secrets_detection(self, dlp_config, test_dlp_samples):
        """Тест обнаружения корпоративных секретов"""
        for field, value in test_dlp_samples.corporate_data.items():
            response = requests.post(
                f"{dlp_config['service_url']}/api/v1/dlp/scan",
                json={"content": value}
            )
            assert response.status_code == 200
            result = response.json()
            assert result["violations"]
            assert any(violation["type"] == "CORPORATE_SECRET" for violation in result["violations"])
            
    @pytest.mark.asyncio
    async def test_policy_enforcement(self, dlp_config):
        """Тест применения политик безопасности"""
        # Тестовая политика: запрет отправки персональных данных
        policy = {
            "name": "No_PII",
            "rules": [
                {
                    "type": "PII",
                    "action": "BLOCK"
                }
            ]
        }
        
        # Применяем политику
        response = requests.post(
            f"{dlp_config['service_url']}/api/v1/dlp/policy",
            json=policy
        )
        assert response.status_code == 201
        
        # Пытаемся отправить персональные данные
        response = requests.post(
            f"{dlp_config['service_url']}/api/v1/dlp/scan",
            json={"content": "test@example.com"}
        )
        assert response.status_code == 403  # Forbidden
        
        # Проверяем лог аудита
        audit_response = requests.get(
            f"{dlp_config['service_url']}/api/v1/dlp/audit"
        )
        assert audit_response.status_code == 200
        audit_logs = audit_response.json()
        assert any(
            log["action"] == "BLOCK" and 
            log["reason"] == "No_PII policy violation" 
            for log in audit_logs
        )
