import os
import json
import subprocess
import time
from datetime import datetime
import logging
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/automation/sequential_setup.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("sequential_setup")

class SequentialSetup:
    def __init__(self):
        self.current_step = 0
        self.steps = []
        self.load_steps()
        self.attempts = 0
        self.max_attempts = 5
        
    def load_steps(self):
        """Загрузка шагов из конфигурации"""
        with open('automation/steps_config.json', 'r') as f:
            self.steps = json.load(f)['steps']
    
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
    
    def execute_step(self, step: dict):
        """Выполнение одного шага"""
        logger.info(f"\nExecuting step {self.current_step + 1}: {step['name']}")
        logger.info(f"Description: {step['description']}")
        
        # Выполнение действий
        if 'actions' in step:
            for action in step['actions']:
                logger.info(f"\nRunning action: {action['name']}")
                if not self.run_command(action['command']):
                    logger.error(f"Action {action['name']} failed")
                    return False
        
        # Проверка результатов
        if 'checks' in step:
            for check in step['checks']:
                logger.info(f"\nChecking result: {check['name']}")
                if not self.run_command(check['command']):
                    logger.error(f"Check {check['name']} failed")
                    return False
        
        logger.info(f"Step {self.current_step + 1} completed successfully")
        return True
    
    def run_sequence(self):
        """Запуск последовательного выполнения шагов"""
        while True:
            self.attempts += 1
            logger.info(f"\nStarting attempt {self.attempts}")
            
            for step in self.steps:
                if not self.execute_step(step):
                    logger.error(f"Step {self.current_step + 1} failed, restarting sequence")
                    break
                
                self.current_step += 1
                
                if self.current_step == len(self.steps):
                    logger.info("\nAll steps completed successfully!")
                    logger.info("Final check passed!")
                    return True
            
            if self.attempts >= self.max_attempts:
                logger.error(f"Maximum attempts ({self.max_attempts}) reached. Exiting.")
                return False
            
            logger.info("\nRestarting sequence...")
            self.current_step = 0
            time.sleep(5)  # Пауза перед новой попыткой

def main():
    setup = SequentialSetup()
    success = setup.run_sequence()
    
    if success:
        logger.info("Setup completed successfully!")
    else:
        logger.error("Setup failed after maximum attempts")

if __name__ == "__main__":
    main()
