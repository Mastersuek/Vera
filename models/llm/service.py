import grpc
from concurrent import futures
import time
import logging
from typing import Optional

from proto import model_pb2
from proto import model_pb2_grpc
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelService(model_pb2_grpc.ModelServiceServicer):
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        self.load_model()

    def load_model(self):
        """Загрузка и квантизация модели"""
        try:
            logger.info("Загрузка модели...")
            self.model = AutoModelForCausalLM.from_pretrained(
                "/app/model",
                torch_dtype=torch.float16,
                device_map="auto"
            )
            self.tokenizer = AutoTokenizer.from_pretrained("/app/model")
            self.is_loaded = True
            logger.info("Модель успешно загружена")
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели: {str(e)}")
            raise

    def Generate(self, request, context):
        """Генерация текста"""
        if not self.is_loaded:
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            context.set_details("Модель не загружена")
            return model_pb2.GenerateResponse()

        try:
            logger.info(f"Генерация текста для: {request.prompt}")
            
            # Токенизация входного текста
            inputs = self.tokenizer(request.prompt, return_tensors="pt").to(self.model.device)
            
            # Генерация ответа
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=request.max_length,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    do_sample=True
                )
            
            # Декодирование ответа
            response_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            logger.info(f"Сгенерированный текст: {response_text}")
            return model_pb2.GenerateResponse(text=response_text)
        
        except Exception as e:
            logger.error(f"Ошибка при генерации: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return model_pb2.GenerateResponse()

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=3))
    model_pb2_grpc.add_ModelServiceServicer_to_server(ModelService(), server)
    server.add_insecure_port("[::]:50051")
    logger.info("Starting model server on port 50051...")
    server.start()
    
    try:
        while True:
            time.sleep(60 * 60 * 24)  # Сервер будет работать бесконечно
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()
