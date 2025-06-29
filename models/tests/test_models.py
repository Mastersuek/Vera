import unittest
import requests
import time
from update_models import ModelUpdater

class TestModelSystem(unittest.TestCase):
    def setUp(self):
        self.updater = ModelUpdater()
        self.test_prompt = "Привет, как дела?"
        self.test_models = ["bloom", "bart", "mpnet"]

    def test_model_status(self):
        """Тест проверки статуса моделей"""
        status = self.updater.get_model_status()
        for model_name in self.test_models:
            self.assertIn(model_name, status)
            self.assertIn('status', status[model_name])
            self.assertIn('ports', status[model_name])

    def test_model_generation(self):
        """Тест генерации текста"""
        for model_name in self.test_models:
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
            self.assertEqual(response.status_code, 200)
            self.assertIn('text', response.json())

    def test_model_update(self):
        """Тест обновления модели"""
        # Проверяем статус до обновления
        initial_status = self.updater.get_model_status()
        
        # Обновляем модель
        update_result = self.updater.update_model("bloom")
        self.assertTrue(update_result)
        
        # Ждем немного, чтобы изменения вступили в силу
        time.sleep(5)
        
        # Проверяем статус после обновления
        final_status = self.updater.get_model_status()
        
        # Проверяем, что статус изменился
        self.assertNotEqual(
            initial_status["bloom"],
            final_status["bloom"]
        )

    def test_health_check(self):
        """Тест проверки здоровья сервисов"""
        for model_name in self.test_models:
            port = self.updater.models[model_name]['port']
            response = requests.get(f"http://localhost:{port - 50000}/health")
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()['healthy'])

if __name__ == '__main__':
    unittest.main()
