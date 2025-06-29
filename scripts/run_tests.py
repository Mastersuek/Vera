import os
import json
import subprocess
import time
from datetime import datetime
import logging
import asyncio

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/automation/tests.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("test_runner")

class TestRunner:
    def __init__(self):
        self.current_test = 1
        self.results = {}
        self.failed = False
        
    def run_command(self, command: str):
        """Выполнение команды с логированием"""
        try:
            logger.info(f"Running command: {command}")
            result = subprocess.run(command.split(), capture_output=True, text=True)
            logger.info(f"Command output: {result.stdout}")
            if result.returncode != 0:
                logger.error(f"Command failed: {result.stderr}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error running command: {str(e)}")
            return False
    
    def check_service_status(self, service: str):
        """Проверка состояния сервиса"""
        try:
            result = subprocess.run([
                "docker", "compose", "ps", "--status", "running", service
            ], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def run_test(self, test: dict):
        """Выполнение одного теста"""
        logger.info(f"\nStarting test {self.current_test}: {test['name']}")
        logger.info("Description: " + test['description'])
        
        try:
            # Выполнение предварительных проверок
            if 'actions' in test:
                for action in test['actions']:
                    logger.info(f"\nRunning action: {action['name']}")
                    if not self.run_command(action['command']):
                        logger.error(f"Action {action['name']} failed")
                        self.failed = True
                        break
            
            # Проверка результатов
            if 'checks' in test and not self.failed:
                for check in test['checks']:
                    logger.info(f"\nChecking result: {check['name']}")
                    if not self.run_command(check['command']):
                        logger.error(f"Check {check['name']} failed")
                        self.failed = True
                        break
            
            self.log_test_result(test)
            
        except Exception as e:
            logger.error(f"Test {self.current_test} failed: {str(e)}")
            self.log_test_error(test, str(e))
            self.failed = True
    
    def log_test_result(self, test: dict):
        """Логирование результата теста"""
        self.results[self.current_test] = {
            'name': test['name'],
            'description': test['description'],
            'timestamp': datetime.now().isoformat(),
            'status': 'success' if not self.failed else 'failed',
            'details': test.get('details', {})
        }
        self.save_results()
        self.failed = False
    
    def log_test_error(self, test: dict, error: str):
        """Логирование ошибки теста"""
        self.results[self.current_test] = {
            'name': test['name'],
            'description': test['description'],
            'timestamp': datetime.now().isoformat(),
            'status': 'error',
            'error': error,
            'details': test.get('details', {})
        }
        self.save_results()
    
    def save_results(self):
        """Сохранение результатов"""
        os.makedirs('logs/automation', exist_ok=True)
        with open('logs/automation/test_results.json', 'w') as f:
            json.dump(self.results, f, indent=4)

def load_test_plan():
    """Загрузка плана тестирования"""
    with open('automation/test_plan.json', 'r') as f:
        return json.load(f)

def main():
    try:
        # Создаем директории для логов
        os.makedirs('logs/automation', exist_ok=True)
        
        # Загружаем план тестирования
        plan = load_test_plan()
        
        # Создаем экземпляр runner
        runner = TestRunner()
        
        # Выполняем все тесты
        for test in plan['steps']:
            runner.run_test(test)
            runner.current_test += 1
            
            # Делаем паузу между тестами
            time.sleep(5)
            
    except Exception as e:
        logger.error(f"Testing failed: {str(e)}")

if __name__ == "__main__":
    main()
