import unittest
import requests
import time
import random
from update_models import ModelUpdater

class TestEdgeCases(unittest.TestCase):
    def setUp(self):
        self.updater = ModelUpdater()
        self.test_prompt = "Привет, как дела?"
        self.test_models = ["bloom", "bart", "mpnet"]

    def test_load_large_input(self):
        """Тест на загрузку большого входа"""
        large_input = "a" * 10000  # 10KB текста
        for model_name in self.test_models:
            port = self.updater.models[model_name]['port']
            response = requests.post(
                f"http://localhost:{port - 50000}/generate",
                json={
                    "prompt": large_input,
                    "max_length": 100,
                    "temperature": 0.7,
                    "top_p": 0.9
                },
                timeout=30
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn('text', response.json())

    def test_concurrent_requests(self):
        """Тест на одновременные запросы"""
        num_requests = 10
        responses = []
        
        def send_request():
            model_name = random.choice(self.test_models)
            port = self.updater.models[model_name]['port']
            response = requests.post(
                f"http://localhost:{port - 50000}/generate",
                json={
                    "prompt": self.test_prompt,
                    "max_length": 50,
                    "temperature": 0.7,
                    "top_p": 0.9
                }
            )
            responses.append(response)

        # Создаем список потоков
        threads = []
        for _ in range(num_requests):
            thread = threading.Thread(target=send_request)
            threads.append(thread)
            thread.start()

        # Ждем завершения всех потоков
        for thread in threads:
            thread.join()

        # Проверяем результаты
        for response in responses:
            self.assertEqual(response.status_code, 200)
            self.assertIn('text', response.json())

    def test_invalid_parameters(self):
        """Тест на обработку некорректных параметров"""
        for model_name in self.test_models:
            port = self.updater.models[model_name]['port']
            
            # Некорректный max_length
            response = requests.post(
                f"http://localhost:{port - 50000}/generate",
                json={
                    "prompt": self.test_prompt,
                    "max_length": -1,
                    "temperature": 0.7,
                    "top_p": 0.9
                }
            )
            self.assertEqual(response.status_code, 400)

            # Некорректный temperature
            response = requests.post(
                f"http://localhost:{port - 50000}/generate",
                json={
                    "prompt": self.test_prompt,
                    "max_length": 50,
                    "temperature": -0.1,
                    "top_p": 0.9
                }
            )
            self.assertEqual(response.status_code, 400)

            # Некорректный top_p
            response = requests.post(
                f"http://localhost:{port - 50000}/generate",
                json={
                    "prompt": self.test_prompt,
                    "max_length": 50,
                    "temperature": 0.7,
                    "top_p": 1.1
                }
            )
            self.assertEqual(response.status_code, 400)

    def test_memory_leak(self):
        """Тест на утечку памяти"""
        model_name = random.choice(self.test_models)
        port = self.updater.models[model_name]['port']
        
        # Получаем начальное использование памяти
        initial_memory = float(requests.get(
            f"http://localhost:9090/api/v1/query",
            params={
                'query': f'process_resident_memory_bytes{{service="{model_name}"}} / 1024 / 1024 / 1024'
            }
        ).json()['data']['result'][0]['value'][1])

        # Отправляем много запросов
        for _ in range(100):
            requests.post(
                f"http://localhost:{port - 50000}/generate",
                json={
                    "prompt": self.test_prompt,
                    "max_length": 50,
                    "temperature": 0.7,
                    "top_p": 0.9
                }
            )

        # Ждем немного, чтобы память освободилась
        time.sleep(10)

        # Получаем финальное использование памяти
        final_memory = float(requests.get(
            f"http://localhost:9090/api/v1/query",
            params={
                'query': f'process_resident_memory_bytes{{service="{model_name}"}} / 1024 / 1024 / 1024'
            }
        ).json()['data']['result'][0]['value'][1])

        # Проверяем, что память не увеличилась более чем на 10%
        self.assertTrue(final_memory <= initial_memory * 1.1)

    def test_graceful_shutdown(self):
        """Тест на корректное завершение работы"""
        model_name = random.choice(self.test_models)
        container = self.updater.client.containers.get(model_name)
        
        # Отправляем запрос
        response = requests.post(
            f"http://localhost:{container.ports['8000/tcp'][0]['HostPort']}/generate",
            json={
                "prompt": self.test_prompt,
                "max_length": 50,
                "temperature": 0.7,
                "top_p": 0.9
            }
        )
        self.assertEqual(response.status_code, 200)

        # Останавливаем контейнер
        container.stop()

        # Проверяем, что сервис недоступен
        with self.assertRaises(requests.exceptions.ConnectionError):
            requests.post(
                f"http://localhost:{container.ports['8000/tcp'][0]['HostPort']}/generate",
                json={
                    "prompt": self.test_prompt,
                    "max_length": 50,
                    "temperature": 0.7,
                    "top_p": 0.9
                }
            )

if __name__ == '__main__':
    unittest.main()
