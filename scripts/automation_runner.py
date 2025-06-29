import logging
import asyncio
import os
import json
from datetime import datetime
import uv
import subprocess
from uv import Process

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/automation/automation.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("automation_runner")

class AutomationRunner:
    def __init__(self):
        self.current_step = 1
        self.results = {}
        self.processes = []
        
    async def run_step(self, step: dict):
        """Выполнение одного шага автоматизации"""
        logger.info(f"Starting step {self.current_step}: {step['name']}")
        
        try:
            # Выполнение предварительных проверок
            await self.pre_checks(step)
            
            # Выполнение основных действий
            await self.main_actions(step)
            
            # Проверка результатов
            await self.check_results(step)
            
            # Логирование результата
            self.log_step_result(step)
            
            return True
            
        except Exception as e:
            logger.error(f"Step {self.current_step} failed: {str(e)}")
            self.log_step_error(step, str(e))
            return False
    
    async def pre_checks(self, step: dict):
        """Предварительные проверки"""
        if 'pre_checks' in step:
            for check in step['pre_checks']:
                logger.info(f"Running pre-check: {check['name']}")
                result = await self.run_check(check)
                assert result, f"Pre-check {check['name']} failed"
    
    async def main_actions(self, step: dict):
        """Основные действия шага"""
        if 'actions' in step:
            for action in step['actions']:
                logger.info(f"Running action: {action['name']}")
                await self.run_action(action)
    
    async def check_results(self, step: dict):
        """Проверка результатов"""
        if 'checks' in step:
            for check in step['checks']:
                logger.info(f"Checking result: {check['name']}")
                result = await self.run_check(check)
                assert result, f"Check {check['name']} failed"
    
    async def run_check(self, check: dict):
        """Выполнение проверки"""
        if check['type'] == 'service_status':
            return await self.check_service_status(check['service'])
        elif check['type'] == 'connection':
            return await self.check_connection(check['host'], check['port'])
        elif check['type'] == 'data_state':
            return await self.check_data_state(check['source'])
        return False
    
    async def run_action(self, action: dict):
        """Выполнение действия"""
        if action['type'] == 'start_service':
            await self.start_service(action['service'])
        elif action['type'] == 'restart_service':
            await self.restart_service(action['service'])
        elif action['type'] == 'run_command':
            await self.run_command(action['command'])
    
    async def check_service_status(self, service_name: str):
        """Проверка состояния сервиса"""
        try:
            container = self.docker_client.containers.get(f"vera-{service_name}")
            return container.status == "running"
        except:
            return False
    
    async def check_connection(self, host: str, port: int):
        """Проверка сетевого соединения"""
        try:
            result = subprocess.run([
                "nc", "-zv", host, str(port)
            ], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    async def check_data_state(self, source: str):
        """Проверка состояния данных"""
        try:
            if source == 'redis':
                result = subprocess.run([
                    "docker", "exec", "vera-redis", "redis-cli", "info", "persistence"
                ], capture_output=True, text=True)
                return "rdb_last_save_time" in result.stdout
            elif source == 'postgres':
                result = subprocess.run([
                    "docker", "exec", "vera-postgres", "psql", "-U", "postgres", "-c", "SELECT COUNT(*) FROM information_schema.tables;"
                ], capture_output=True, text=True)
                return int(result.stdout.strip().split()[-1]) > 0
            return False
        except:
            return False
    
    async def start_service(self, service_name: str):
        """Запуск сервиса"""
        try:
            subprocess.run(["docker", "compose", "up", "-d", service_name], check=True)
            return True
        except:
            return False
    
    async def restart_service(self, service_name: str):
        """Перезапуск сервиса"""
        try:
            subprocess.run(["docker", "compose", "restart", service_name], check=True)
            return True
        except:
            return False
    
    async def run_command(self, command: str):
        """Выполнение команды с помощью uv"""
        try:
            process = Process()
            process.spawn(command.split())
            self.processes.append(process)
            await process.wait()
            return True
        except Exception as e:
            logger.error(f"Command failed: {str(e)}")
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
        with open('logs/automation/results.json', 'w') as f:
            json.dump(self.results, f, indent=4)

def load_plan():
    """Загрузка плана автоматизации"""
    with open('automation/automation_plan.json', 'r') as f:
        return json.load(f)

async def main():
    try:
        # Создаем директории для логов
        os.makedirs('logs/automation', exist_ok=True)
        
        # Загружаем план
        plan = load_plan()
        
        # Создаем экземпляр runner
        runner = AutomationRunner()
        
        # Выполняем все шаги
        for step in plan['steps']:
            success = await runner.run_step(step)
            if not success:
                logger.error(f"Step {runner.current_step} failed. Stopping execution.")
                break
            runner.current_step += 1
    except Exception as e:
        logger.error(f"Automation failed: {str(e)}")
    finally:
        # Очищаем процессы
        for process in runner.processes:
            try:
                process.kill()
            except:
                pass

if __name__ == "__main__":
    asyncio.run(main())
