import os
import json
import subprocess
import time
from datetime import datetime
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/automation/debug.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("debug_services")

class ServiceDebugger:
    def __init__(self):
        self.results = {}
        
    def run_command(self, command: str):
        """Выполнение команды с логированием"""
        try:
            logger.info(f"Running command: {command}")
            result = subprocess.run(command.split(), capture_output=True, text=True)
            logger.info(f"Command output: {result.stdout}")
            if result.returncode != 0:
                logger.error(f"Command failed: {result.stderr}")
            return result
        except Exception as e:
            logger.error(f"Error running command: {str(e)}")
            return None
    
    def debug_postgres(self):
        """Отладка PostgreSQL"""
        logger.info("\nDebugging PostgreSQL...")
        
        # Проверка контейнера
        container = self.run_command("docker ps -f name=vera-postgres")
        
        # Проверка логов
        logs = self.run_command("docker logs vera-postgres")
        
        # Проверка конфигурации
        config = self.run_command("docker exec vera-postgres cat /etc/postgresql/postgresql.conf")
        
        return {
            'container': container.stdout if container else None,
            'logs': logs.stdout if logs else None,
            'config': config.stdout if config else None
        }
    
    def debug_redis(self):
        """Отладка Redis"""
        logger.info("\nDebugging Redis...")
        
        # Проверка контейнера
        container = self.run_command("docker ps -f name=vera-redis")
        
        # Проверка логов
        logs = self.run_command("docker logs vera-redis")
        
        # Проверка конфигурации
        config = self.run_command("docker exec vera-redis cat /etc/redis/redis.conf")
        
        return {
            'container': container.stdout if container else None,
            'logs': logs.stdout if logs else None,
            'config': config.stdout if config else None
        }
    
    def debug_network(self):
        """Отладка сети"""
        logger.info("\nDebugging network...")
        
        # Проверка сетевых соединений
        postgres_check = self.run_command("nc -zv localhost 5432")
        redis_check = self.run_command("nc -zv localhost 6379")
        
        # Проверка Docker сети
        network = self.run_command("docker network ls")
        
        return {
            'postgres_check': postgres_check.stdout if postgres_check else None,
            'redis_check': redis_check.stdout if redis_check else None,
            'network': network.stdout if network else None
        }
    
    def debug_recovery(self):
        """Отладка системы восстановления"""
        logger.info("\nDebugging auto recovery...")
        
        # Проверка состояния сервисов
        services = self.run_command("docker compose ps")
        
        # Проверка конфигурации восстановления
        config = self.run_command("cat scripts/auto_recovery.py")
        
        return {
            'services': services.stdout if services else None,
            'config': config.stdout if config else None
        }
    
    def save_debug_results(self, results):
        """Сохранение результатов отладки"""
        os.makedirs('logs/automation', exist_ok=True)
        with open('logs/automation/debug_results.json', 'w') as f:
            json.dump(results, f, indent=4)

def main():
    debugger = ServiceDebugger()
    
    debug_results = {
        'postgres': debugger.debug_postgres(),
        'redis': debugger.debug_redis(),
        'network': debugger.debug_network(),
        'recovery': debugger.debug_recovery()
    }
    
    debugger.save_debug_results(debug_results)

if __name__ == "__main__":
    main()
