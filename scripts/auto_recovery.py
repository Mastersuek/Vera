import docker
import subprocess
import logging
import time
import os
from datetime import datetime
import json

logger = logging.getLogger("auto_recovery")

# Конфигурация восстановления
CONFIG = {
    "check_interval": 30,  # Интервал проверки в секундах
    "max_retries": 3,     # Максимальное количество попыток восстановления
    "restart_delay": 10,  # Задержка после перезапуска в секундах
    "healthcheck_timeout": 10,  # Таймаут для проверки здоровья
    "critical_services": ["postgres", "redis", "app"]  # Критические сервисы
}

class AutoRecovery:
    def __init__(self):
        self.docker_client = docker.from_env()
        self.last_recovery = {}
        self.setup_logging()
        
    def setup_logging(self):
        """Настройка логирования"""
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'recovery')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f'recovery_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    
    def check_service_health(self, service_name):
        """Проверка здоровья сервиса"""
        try:
            container = self.docker_client.containers.get(f"vera-{service_name}")
            return container.status == "running"
        except Exception as e:
            logger.error(f"Error checking {service_name}: {str(e)}")
            return False
    
    def restart_service(self, service_name):
        """Перезапуск сервиса"""
        try:
            container = self.docker_client.containers.get(f"vera-{service_name}")
            logger.info(f"Restarting {service_name}...")
            container.restart()
            time.sleep(CONFIG["restart_delay"])
            return True
        except Exception as e:
            logger.error(f"Error restarting {service_name}: {str(e)}")
            return False
    
    def check_and_recover(self):
        """Проверка и восстановление сервисов"""
        for service in CONFIG["critical_services"]:
            if not self.check_service_health(service):
                if service not in self.last_recovery:
                    self.last_recovery[service] = 0
                
                if self.last_recovery[service] < CONFIG["max_retries"]:
                    if self.restart_service(service):
                        self.last_recovery[service] = 0
                        logger.info(f"{service} recovered successfully")
                    else:
                        self.last_recovery[service] += 1
                        logger.warning(f"Failed to recover {service}, retry {self.last_recovery[service]}/{CONFIG['max_retries']}")
                else:
                    logger.error(f"Max retries reached for {service}, manual intervention required")
                    # Отправка уведомления о критической ситуации
                    self.send_alert(f"Critical failure: {service} failed to recover after {CONFIG['max_retries']} attempts")
    
    def send_alert(self, message):
        """Отправка уведомления о критической ситуации"""
        try:
            # Здесь можно добавить интеграцию с системой уведомлений
            logger.error(f"ALERT: {message}")
        except Exception as e:
            logger.error(f"Error sending alert: {str(e)}")
    
    def run(self):
        """Основной цикл мониторинга"""
        logger.info("Starting auto-recovery service...")
        
        while True:
            try:
                self.check_and_recover()
                time.sleep(CONFIG["check_interval"])
            except KeyboardInterrupt:
                logger.info("Stopping auto-recovery service...")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                time.sleep(CONFIG["check_interval"])

if __name__ == "__main__":
    recovery = AutoRecovery()
    recovery.run()
