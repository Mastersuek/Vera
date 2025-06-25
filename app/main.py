from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
import os
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Создание экземпляра приложения
app = FastAPI(
    title="Vera Platform",
    description="Платформа для анализа данных с искусственным интеллектом",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "Аутентификация",
            "description": "Аутентификация и авторизация пользователей"
        },
        {
            "name": "Данные",
            "description": "Работа с данными и анализ"
        },
        {
            "name": "Администрирование",
            "description": "Функции администратора"
        }
    ]
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модели данных
class Message(BaseModel):
    message: str
    details: Optional[Dict[str, Any]] = None

# Обработчики ошибок
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"ошибка": exc.detail}
    )

# Основные маршруты
@app.get("/", tags=["Основное"])
async def read_root():
    """
    Корневой эндпоинт API
    
    Возвращает приветственное сообщение и статус API
    """
    return {
        "приложение": "Vera Platform",
        "версия": "1.0.0",
        "статус": "работает",
        "документация": "/docs"
    }

@app.get("/health", tags=["Система"])
async def health_check():
    """
    Проверка работоспособности сервиса
    
    Используется для мониторинга и проверки доступности сервиса
    """
    return {
        "статус": "ok",
        "сервис": "Vera API",
        "версия": "1.0.0"
    }

# Защищенный маршрут (пример)
@app.get("/api/secure", tags=["Аутентификация"])
async def secure_endpoint():
    """
    Пример защищенного эндпоинта
    
    Требует аутентификации пользователя
    """
    return {
        "сообщение": "Доступ к защищенному ресурсу разрешен",
        "пользователь": "тестовый_пользователь",
        "права": ["чтение", "запись"]
    }

# Запуск приложения
if __name__ == "__main__":
    import uvicorn
    logger.info("Запуск сервера Vera Platform...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
