from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
import uvicorn
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Vera Core",
    description="Движок искусственного интеллекта и машинного обучения для платформы Vera",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "Основные",
            "description": "Основные эндпоинты API"
        },
        {
            "name": "Аутентификация",
            "description": "Аутентификация и управление пользователями"
        },
        {
            "name": "Модели",
            "description": "Управление моделями машинного обучения"
        }
    ]
)

# Схема аутентификации OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.get("/", tags=["Основные"])
async def root():
    """
    Корневой эндпоинт, возвращает приветственное сообщение.
    """
    return {"сообщение": "Добро пожаловать в Vera Core - движок искусственного интеллекта"}

@app.get("/health", tags=["Основные"])
async def health_check():
    """
    Проверка работоспособности сервиса.
    
    Возвращает:
        dict: Статус сервиса
    """
    return {"статус": "работает"}

# Пример защищенного эндпоинта
@app.get("/api/v1/secure", tags=["Аутентификация"])
async def secure_endpoint(token: str = Depends(oauth2_scheme)):
    """
    Пример защищенного эндпоинта, требующего аутентификации.
    
    Параметры:
        token (str): Токен доступа
        
    Возвращает:
        dict: Сообщение о доступе
    """
    # В реальном приложении здесь должна быть валидация токена
    return {"сообщение": "Доступ к защищенному ресурсу разрешен"}

# Обработчик ошибок 404
@app.exception_handler(404)
async def not_found_exception_handler(request, exc):
    return {"ошибка": "Запрашиваемый ресурс не найден"}

# Обработчик общих ошибок
@app.exception_handler(500)
async def server_error_exception_handler(request, exc):
    logger.error(f"Ошибка сервера: {exc}")
    return {"ошибка": "Внутренняя ошибка сервера"}

if __name__ == "__main__":
    logger.info("Запуск сервера Vera Core...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
