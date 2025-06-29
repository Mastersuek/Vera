import docker
import requests
import json
import time
from typing import Dict, List

# Конфигурация моделей
MODELS_CONFIG = {
    "bloom": {
        "name": "bigscience/bloom-560m",
        "port": 50051,
        "container": "bloom",
        "version": "latest"
    },
    "bart": {
        "name": "facebook/bart-large-mnli",
        "port": 50052,
        "container": "bart",
        "version": "latest"
    },
    "mpnet": {
        "name": "sentence-transformers/all-mpnet-base-v2",
        "port": 50053,
        "container": "mpnet",
        "version": "latest"
    }
}

class ModelUpdater:
    def __init__(self):
        self.client = docker.from_env()
        self.models = MODELS_CONFIG

    def check_model_updates(self) -> Dict:
        """Проверяет наличие обновлений для моделей"""
        updates_available = {}
        
        for model_name, config in self.models.items():
            try:
                # Получаем текущий образ
                current_image = self.client.images.get(f"{config['name']}:{config['version']}")
                
                # Проверяем наличие обновлений
                repo_tags = self.client.images.list(name=config['name'])
                if not repo_tags:
                    updates_available[model_name] = True
                    continue
                
                # Сравниваем размеры образов
                current_size = current_image.attrs['Size']
                latest_size = repo_tags[0].attrs['Size']
                
                updates_available[model_name] = current_size != latest_size
                
            except Exception as e:
                print(f"Ошибка при проверке {model_name}: {str(e)}")
                updates_available[model_name] = False
        
        return updates_available

    def update_model(self, model_name: str) -> bool:
        """Обновляет указанную модель"""
        try:
            config = self.models[model_name]
            
            # Останавливаем контейнер
            container = self.client.containers.get(config['container'])
            container.stop()
            container.remove()
            
            # Удаляем старый образ
            self.client.images.remove(f"{config['name']}:{config['version']}")
            
            # Скачиваем новый образ
            print(f"Скачивание нового образа для {model_name}...")
            self.client.images.pull(config['name'], tag=config['version'])
            
            # Запускаем новый контейнер
            print(f"Запуск нового контейнера для {model_name}...")
            self.client.containers.run(
                f"{config['name']}:{config['version']}",
                detach=True,
                ports={
                    '50051/tcp': config['port'],
                    '8000/tcp': config['port'] - 50000
                },
                environment={
                    'MODEL_NAME': config['name']
                },
                volumes={
                    'model_cache': {'bind': '/app/model', 'mode': 'rw'}
                },
                name=config['container'],
                restart_policy={'Name': 'always'}
            )
            
            # Ждем, пока контейнер запустится
            time.sleep(10)
            
            # Проверяем статус
            new_container = self.client.containers.get(config['container'])
            if new_container.status == 'running':
                print(f"Модель {model_name} успешно обновлена")
                return True
                
            print(f"Ошибка при обновлении {model_name}")
            return False
            
        except Exception as e:
            print(f"Ошибка при обновлении {model_name}: {str(e)}")
            return False

    def update_all_models(self) -> Dict:
        """Обновляет все модели"""
        results = {}
        updates = self.check_model_updates()
        
        for model_name, needs_update in updates.items():
            if needs_update:
                results[model_name] = self.update_model(model_name)
            else:
                results[model_name] = False
        
        return results

    def get_model_status(self) -> Dict:
        """Получает статус всех моделей"""
        status = {}
        
        for model_name, config in self.models.items():
            try:
                container = self.client.containers.get(config['container'])
                status[model_name] = {
                    'status': container.status,
                    'ports': container.ports,
                    'image': container.image.tags[0] if container.image.tags else 'unknown'
                }
            except Exception as e:
                status[model_name] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return status

if __name__ == '__main__':
    updater = ModelUpdater()
    
    # Проверка статуса
    print("\nТекущий статус моделей:")
    status = updater.get_model_status()
    print(json.dumps(status, indent=2))
    
    # Проверка обновлений
    print("\nПроверка обновлений:")
    updates = updater.check_model_updates()
    print(json.dumps(updates, indent=2))
    
    # Обновление всех моделей
    print("\nОбновление моделей:")
    results = updater.update_all_models()
    print(json.dumps(results, indent=2))
    
    # Финальный статус
    print("\nФинальный статус моделей:")
    status = updater.get_model_status()
    print(json.dumps(status, indent=2))
