import pytest
import asyncio
import docker
import subprocess
import os
import time
from datetime import datetime
import logging

logger = logging.getLogger("test_recovery")

@pytest.fixture(scope="module")
def docker_client():
    """Клиент Docker для управления контейнерами"""
    return docker.from_env()

@pytest.fixture(scope="module")
def test_config():
    """Конфигурация для тестов восстановления"""
    return {
        "wait_time": 30,  # Время ожидания между операциями
        "max_retries": 3,  # Максимальное количество попыток восстановления
        "healthcheck_timeout": 10  # Таймаут для проверки здоровья сервисов
    }

@pytest.mark.asyncio
class TestSystemRecovery:
    async def test_service_restart(self, docker_client, test_config):
        """Тест перезапуска сервисов после сбоя"""
        services = ["postgres", "redis", "app"]
        
        for service in services:
            logger.info(f"Testing restart of {service} service")
            
            # Останавливаем сервис
            container = docker_client.containers.get(f"vera-{service}")
            container.stop()
            logger.info(f"Service {service} stopped")
            
            # Ждем и проверяем статус
            await asyncio.sleep(test_config["wait_time"])
            container = docker_client.containers.get(f"vera-{service}")
            assert container.status == "exited"
            
            # Запускаем сервис
            container.start()
            logger.info(f"Service {service} started")
            
            # Проверяем восстановление
            retries = 0
            while retries < test_config["max_retries"]:
                try:
                    container = docker_client.containers.get(f"vera-{service}")
                    if container.status == "running":
                        logger.info(f"Service {service} recovered successfully")
                        break
                except:
                    retries += 1
                    await asyncio.sleep(test_config["healthcheck_timeout"])
            
            assert container.status == "running"

    async def test_power_cycle(self, docker_client, test_config):
        """Тест восстановления после перезагрузки системы"""
        # Симулируем перезагрузку системы
        logger.info("Simulating system power cycle")
        
        # Останавливаем все сервисы
        containers = docker_client.containers.list()
        for container in containers:
            if container.name.startswith("vera-"):
                container.stop()
        logger.info("All services stopped")
        
        # Ждем и запускаем все сервисы
        await asyncio.sleep(test_config["wait_time"])
        subprocess.run(["docker-compose", "up", "-d"], check=True)
        logger.info("All services started")
        
        # Проверяем состояние всех сервисов
        retries = 0
        while retries < test_config["max_retries"]:
            try:
                containers = docker_client.containers.list()
                running = True
                for container in containers:
                    if container.name.startswith("vera-") and container.status != "running":
                        running = False
                        break
                if running:
                    logger.info("All services recovered successfully")
                    break
            except:
                retries += 1
                await asyncio.sleep(test_config["healthcheck_timeout"])
        
        assert running

    async def test_data_recovery(self, docker_client, test_config):
        """Тест восстановления данных после сбоя"""
        # Тестируем Redis
        redis_container = docker_client.containers.get("vera-redis")
        redis_container.stop()
        logger.info("Redis stopped")
        
        await asyncio.sleep(test_config["wait_time"])
        redis_container.start()
        logger.info("Redis started")
        
        # Проверяем восстановление данных
        result = subprocess.run(
            ["docker", "exec", "vera-redis", "redis-cli", "info", "persistence"],
            capture_output=True,
            text=True
        )
        assert "rdb_last_save_time" in result.stdout
        logger.info("Redis data recovery verified")
        
        # Тестируем PostgreSQL
        pg_container = docker_client.containers.get("vera-postgres")
        pg_container.stop()
        logger.info("PostgreSQL stopped")
        
        await asyncio.sleep(test_config["wait_time"])
        pg_container.start()
        logger.info("PostgreSQL started")
        
        # Проверяем восстановление данных
        result = subprocess.run(
            ["docker", "exec", "vera-postgres", "psql", "-U", "postgres", "-c", "SELECT COUNT(*) FROM information_schema.tables;"],
            capture_output=True,
            text=True
        )
        assert int(result.stdout.strip().split()[-1]) > 0
        logger.info("PostgreSQL data recovery verified")

    async def test_network_recovery(self, docker_client, test_config):
        """Тест восстановления после сетевых сбоев"""
        # Симулируем сетевой сбой
        subprocess.run(["sudo", "iptables", "-A", "OUTPUT", "-d", "localhost", "-j", "DROP"], check=True)
        logger.info("Network outage simulated")
        
        await asyncio.sleep(test_config["wait_time"])
        
        # Восстанавливаем сеть
        subprocess.run(["sudo", "iptables", "-D", "OUTPUT", "-d", "localhost", "-j", "DROP"], check=True)
        logger.info("Network restored")
        
        # Проверяем восстановление сервисов
        retries = 0
        while retries < test_config["max_retries"]:
            try:
                containers = docker_client.containers.list()
                for container in containers:
                    if container.name.startswith("vera-"):
                        container.reload()
                        assert container.status == "running"
                break
            except:
                retries += 1
                await asyncio.sleep(test_config["healthcheck_timeout"])
        
        assert retries < test_config["max_retries"]
        logger.info("Network recovery verified")
