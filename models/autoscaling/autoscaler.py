import docker
import requests
import time
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelAutoscaler:
    def __init__(self):
        self.client = docker.from_env()
        self.models = {
            "bloom": {
                "min_replicas": 1,
                "max_replicas": 5,
                "target_cpu": 70,
                "target_memory": 85,
                "target_latency": 1.0
            },
            "bart": {
                "min_replicas": 1,
                "max_replicas": 3,
                "target_cpu": 70,
                "target_memory": 85,
                "target_latency": 0.5
            },
            "mpnet": {
                "min_replicas": 1,
                "max_replicas": 3,
                "target_cpu": 70,
                "target_memory": 85,
                "target_latency": 0.2
            }
        }

    def get_metrics(self, model_name: str) -> Dict:
        """Получает метрики для модели"""
        try:
            # Получаем метрики из Prometheus
            response = requests.get(
                'http://localhost:9090/api/v1/query',
                params={
                    'query': f'rate(process_cpu_seconds_total{{service="{model_name}"}}[5m]) * 100'
                }
            )
            cpu = response.json()['data']['result'][0]['value'][1]

            response = requests.get(
                'http://localhost:9090/api/v1/query',
                params={
                    'query': f'process_resident_memory_bytes{{service="{model_name}"}} / 1024 / 1024 / 1024'
                }
            )
            memory = response.json()['data']['result'][0]['value'][1]

            response = requests.get(
                'http://localhost:9090/api/v1/query',
                params={
                    'query': f'histogram_quantile(0.95, sum(rate(model_request_duration_seconds_bucket{{service="{model_name}"}}[5m])) by (le))'
                }
            )
            latency = response.json()['data']['result'][0]['value'][1]

            return {
                'cpu': float(cpu),
                'memory': float(memory),
                'latency': float(latency)
            }

        except Exception as e:
            logger.error(f"Ошибка при получении метрик для {model_name}: {str(e)}")
            return None

    def scale_model(self, model_name: str, target_replicas: int) -> bool:
        """Масштабирует модель"""
        try:
            # Получаем текущее количество реплик
            current_replicas = len(self.client.containers.list(
                filters={'name': model_name}
            ))

            # Если количество реплик не изменилось, ничего не делаем
            if current_replicas == target_replicas:
                return True

            # Останавливаем лишние реплики
            if target_replicas < current_replicas:
                containers = self.client.containers.list(
                    filters={'name': model_name}
                )
                for container in containers[target_replicas:]:
                    container.stop()
                    container.remove()

            # Запускаем новые реплики
            elif target_replicas > current_replicas:
                for _ in range(target_replicas - current_replicas):
                    self.client.containers.run(
                        f"{model_name}:latest",
                        detach=True,
                        ports={
                            '50051/tcp': None,
                            '8000/tcp': None
                        },
                        environment={
                            'MODEL_NAME': model_name
                        },
                        volumes={
                            'model_cache': {'bind': '/app/model', 'mode': 'rw'}
                        },
                        name=f"{model_name}-replica-{time.time_ns()}",
                        restart_policy={'Name': 'always'}
                    )

            logger.info(f"Масштабирование {model_name} до {target_replicas} реплик")
            return True

        except Exception as e:
            logger.error(f"Ошибка при масштабировании {model_name}: {str(e)}")
            return False

    def decide_scaling(self, metrics: Dict, config: Dict) -> int:
        """Принимает решение о масштабировании"""
        target_replicas = 1

        # Проверяем CPU
        if metrics['cpu'] > config['target_cpu']:
            target_replicas += 1

        # Проверяем память
        if metrics['memory'] > config['target_memory']:
            target_replicas += 1

        # Проверяем латенсию
        if metrics['latency'] > config['target_latency']:
            target_replicas += 1

        # Ограничиваем количеством реплик
        target_replicas = max(config['min_replicas'],
                             min(target_replicas, config['max_replicas']))

        return target_replicas

    def run(self):
        """Основной цикл масштабирования"""
        while True:
            try:
                for model_name, config in self.models.items():
                    metrics = self.get_metrics(model_name)
                    if metrics:
                        target_replicas = self.decide_scaling(metrics, config)
                        self.scale_model(model_name, target_replicas)

                time.sleep(30)  # Проверяем каждые 30 секунд

            except Exception as e:
                logger.error(f"Ошибка в основном цикле: {str(e)}")
                time.sleep(60)  # При ошибке ждем дольше

if __name__ == '__main__':
    autoscaler = ModelAutoscaler()
    autoscaler.run()
