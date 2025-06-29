from typing import Optional
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

class ModelConfig:
    model_name: str = "bigscience/bloom-560m"
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    dtype: torch.dtype = torch.float16
    max_length: int = 512
    temperature: float = 0.7
    top_p: float = 0.9

class ModelManager:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.is_loaded = False

    def load_model(self):
        """Загрузка и подготовка модели"""
        try:
            # Загрузка модели
            self.model = AutoModelForCausalLM.from_pretrained(
                ModelConfig.model_name,
                torch_dtype=ModelConfig.dtype,
                device_map="auto"
            )

            # Загрузка токенизатора
            self.tokenizer = AutoTokenizer.from_pretrained(
                ModelConfig.model_name
            )

            self.is_loaded = True
            return True

        except Exception as e:
            print(f"Ошибка при загрузке модели: {str(e)}")
            return False

    def generate(self, prompt: str, max_length: int = None, temperature: float = None, top_p: float = None):
        """Генерация текста"""
        if not self.is_loaded:
            raise RuntimeError("Модель не загружена")

        try:
            # Подготовка параметров
            max_length = max_length or ModelConfig.max_length
            temperature = temperature or ModelConfig.temperature
            top_p = top_p or ModelConfig.top_p

            # Токенизация входного текста
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

            # Генерация ответа
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=max_length,
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=True
                )

            # Декодирование ответа
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return response

        except Exception as e:
            print(f"Ошибка при генерации: {str(e)}")
            raise
