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
        logging.FileHandler('logs/automation/basic_automation.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("basic_automation")

class BasicAutomation:
    def __init__(self):
        self.current_step = 1
        self.results = {}
        self.processes = []
        
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
    
    def run_step(self, step: dict):
        """Выполнение одного шага"""
        logger.info(f"Starting step {self.current_step}: {step['name']}")
        
        try:
            # Выполнение предварительных проверок
            if 'pre_checks' in step:
                for check in step['pre_checks']:
                    logger.info(f"Running pre-check: {check['name']}")
                    if not self.run_check(check):
                        logger.error(f"Pre-check {check['name']} failed")
                        return False
            
            # Выполнение основных действий
            if 'actions' in step:
                for action in step['actions']:
                    logger.info(f"Running action: {action['name']}")
                    if not self.run_action(action):
                        logger.error(f"Action {action['name']} failed")
                        return False
            
            # Проверка результатов
            if 'checks' in step:
                for check in step['checks']:
                    logger.info(f"Checking result: {check['name']}")
                    if not self.run_check(check):
                        logger.error(f"Check {check['name']} failed")
                        return False
            
            self.log_step_result(step)
            return True
            
        except Exception as e:
            logger.error(f"Step {self.current_step} failed: {str(e)}")
            self.log_step_error(step, str(e))
            return False
    
    def run_check(self, check: dict):
        """Выполнение проверки"""
        if check['type'] == 'service_status':
            return self.check_service_status(check['service'])
        elif check['type'] == 'command':
            return self.run_command(check['command'])
        return False
    
    def run_action(self, action: dict):
        """Выполнение действия"""
        if action['type'] == 'command':
            return self.run_command(action['command'])
        elif action['type'] == 'sleep':
            time.sleep(action['duration'])
            return True
        return False
    
    def log_step_result(self, step: dict):
        """Логирование результата шага"""
        self.results[self.current_step] = {
            'name': step['name'],
            'timestamp': datetime.now().isoformat(),
            'status': 'success',
            'details': step.get('details', {})
        }
        self.save_results()
    
    def log_step_error(self, step: dict, error: str):
        """Логирование ошибки шага"""
        self.results[self.current_step] = {
            'name': step['name'],
            'timestamp': datetime.now().isoformat(),
            'status': 'error',
            'error': error,
            'details': step.get('details', {})
        }
        self.save_results()
    
    def save_results(self):
        """Сохранение результатов"""
        os.makedirs('logs/automation', exist_ok=True)
        with open('logs/automation/results.json', 'w') as f:
            json.dump(self.results, f, indent=4)

def load_plan():
    """Загрузка плана автоматизации"""
    with open('automation/basic_automation_plan.json', 'r') as f:
        return json.load(f)

def main():
    try:
        # Создаем директории для логов
        os.makedirs('logs/automation', exist_ok=True)
        
        # Загружаем план
        plan = load_plan()
        
        # Создаем экземпляр
        automation = BasicAutomation()
        
        # Выполняем все шаги
        for step in plan['steps']:
            success = automation.run_step(step)
            if not success:
                logger.error(f"Step {automation.current_step} failed. Stopping execution.")
                break
            automation.current_step += 1
    except Exception as e:
        logger.error(f"Automation failed: {str(e)}")

if __name__ == "__main__":
    main()
