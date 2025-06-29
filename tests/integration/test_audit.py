import pytest
from .test_config import test_config
import requests
import json
from datetime import datetime
import logging

# Настройка логирования для тестов
logger = logging.getLogger("test_audit")
logger.setLevel(logging.DEBUG)

# Конфигурация для тестов аудита
@pytest.fixture(scope="module")
def audit_config():
    return test_config()

# Тестовые данные для аудита
class TestAuditSamples:
    def __init__(self):
        self.user_actions = [
            {
                "user": "test_user",
                "action": "login",
                "timestamp": datetime.now().isoformat(),
                "status": "success"
            },
            {
                "user": "test_user",
                "action": "data_access",
                "timestamp": datetime.now().isoformat(),
                "resource": "sensitive_data",
                "status": "success"
            },
            {
                "user": "test_user",
                "action": "data_modify",
                "timestamp": datetime.now().isoformat(),
                "resource": "user_profile",
                "status": "success"
            }
        ]
        
        self.security_events = [
            {
                "type": "login_attempt",
                "timestamp": datetime.now().isoformat(),
                "ip_address": "192.168.1.1",
                "status": "failed",
                "reason": "invalid_credentials"
            },
            {
                "type": "data_access",
                "timestamp": datetime.now().isoformat(),
                "resource": "confidential_data",
                "status": "blocked",
                "reason": "insufficient_permissions"
            },
            {
                "type": "api_call",
                "timestamp": datetime.now().isoformat(),
                "endpoint": "/api/v1/sensitive",
                "status": "success",
                "duration_ms": 150
            }
        ]

# Тесты аудита
class TestAuditEngine:
    @pytest.mark.asyncio
    async def test_user_activity_tracking(self, audit_config, test_audit_samples):
        """Тест отслеживания действий пользователей"""
        for action in test_audit_samples.user_actions:
            response = requests.post(
                f"{audit_config['service_url']}/api/v1/audit/user",
                json=action
            )
            assert response.status_code == 201
            
            # Проверяем, что событие записано
            audit_response = requests.get(
                f"{audit_config['service_url']}/api/v1/audit/history",
                params={"user": action["user"]}
            )
            assert audit_response.status_code == 200
            logs = audit_response.json()
            assert any(
                log["action"] == action["action"] and 
                log["timestamp"] == action["timestamp"]
                for log in logs
            )
            
    @pytest.mark.asyncio
    async def test_security_event_tracking(self, audit_config, test_audit_samples):
        """Тест отслеживания событий безопасности"""
        for event in test_audit_samples.security_events:
            response = requests.post(
                f"{audit_config['service_url']}/api/v1/audit/security",
                json=event
            )
            assert response.status_code == 201
            
            # Проверяем алерты
            alert_response = requests.get(
                f"{audit_config['service_url']}/api/v1/audit/alerts",
                params={"type": event["type"]}
            )
            assert alert_response.status_code == 200
            alerts = alert_response.json()
            assert any(
                alert["event_type"] == event["type"] and 
                alert["status"] == event["status"]
                for alert in alerts
            )
            
    @pytest.mark.asyncio
    async def test_log_aggregation(self, audit_config):
        """Тест агрегации логов"""
        # Генерируем несколько событий
        events = [
            {"type": "api_call", "endpoint": "/api/v1/data", "status": "success"},
            {"type": "api_call", "endpoint": "/api/v1/data", "status": "success"},
            {"type": "api_call", "endpoint": "/api/v1/data", "status": "failure"}
        ]
        
        for event in events:
            requests.post(
                f"{audit_config['service_url']}/api/v1/audit/security",
                json=event
            )
        
        # Проверяем агрегированные метрики
        metrics_response = requests.get(
            f"{audit_config['service_url']}/api/v1/audit/metrics",
            params={"type": "api_call"}
        )
        assert metrics_response.status_code == 200
        metrics = metrics_response.json()
        
        assert metrics["total_calls"] == 3
        assert metrics["success_rate"] == 2/3
        assert metrics["failure_rate"] == 1/3
        
    @pytest.mark.asyncio
    async def test_audit_retention(self, audit_config):
        """Тест политики хранения аудита"""
        # Создаем событие для теста
        test_event = {
            "type": "test_event",
            "timestamp": datetime.now().isoformat(),
            "data": {"test": "value"}
        }
        
        response = requests.post(
            f"{audit_config['service_url']}/api/v1/audit/test",
            json=test_event
        )
        assert response.status_code == 201
        
        # Проверяем, что событие сохранено
        event_id = response.json()["id"]
        get_response = requests.get(
            f"{audit_config['service_url']}/api/v1/audit/test/{event_id}"
        )
        assert get_response.status_code == 200
        
        # Проверяем политику хранения
        retention_response = requests.get(
            f"{audit_config['service_url']}/api/v1/audit/retention"
        )
        assert retention_response.status_code == 200
        retention = retention_response.json()
        assert retention["policy"] == "30_days"
        assert retention["type"] == "rolling_window"
