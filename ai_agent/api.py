"""
API роутер для управления моделями ИИ.

Содержит эндпоинты для работы с моделями.
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from loguru import logger

from .models import ModelManager, ModelInfo
from .main import model_manager

# Создаем роутер
router = APIRouter(
    prefix="/models",
    tags=["models"],
    responses={
        404: {"description": "Модель не найдена"},
        500: {"description": "Ошибка сервера"},
    },
)


@router.get("/", response_model=List[Dict[str, Any]])
async def list_models():
    """Возвращает список всех доступных моделей."""
    try:
        return model_manager.list_models()
    except Exception as e:
        logger.error(f"Ошибка при получении списка моделей: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении списка моделей: {str(e)}"
        )


@router.get("/{model_id}", response_model=Dict[str, Any])
async def get_model_info(model_id: str):
    """Возвращает информацию о конкретной модели."""
    try:
        model_info = model_manager.get_model_info(model_id)
        if not model_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Модель {model_id} не найдена"
            )
        return model_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении информации о модели {model_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении информации о модели: {str(e)}"
        )


@router.post("/{model_id}/download", response_model=Dict[str, Any])
async def download_model(model_id: str):
    """Загружает модель из репозитория."""
    try:
        model_info = await model_manager.download_model(model_id)
        return {"status": "success", "model": model_info.to_dict()}
    except Exception as e:
        logger.error(f"Ошибка при загрузке модели {model_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при загрузке модели: {str(e)}"
        )


@router.post("/{model_id}/load", response_model=Dict[str, Any])
async def load_model(model_id: str):
    """Загружает модель в память."""
    try:
        model = await model_manager.get_model(model_id)
        return {"status": "success", "model_id": model_id, "loaded": True}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка при загрузке модели {model_id} в память: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при загрузке модели в память: {str(e)}"
        )


@router.post("/{model_id}/unload", response_model=Dict[str, Any])
async def unload_model(model_id: str):
    """Выгружает модель из памяти."""
    try:
        success = await model_manager.unload_model(model_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Модель {model_id} не найдена или не загружена"
            )
        return {"status": "success", "model_id": model_id, "loaded": False}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при выгрузке модели {model_id} из памяти: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при выгрузке модели из памяти: {str(e)}"
        )


@router.delete("/{model_id}", response_model=Dict[str, Any])
async def delete_model(model_id: str):
    """Удаляет модель из системы."""
    try:
        success = await model_manager.delete_model(model_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Модель {model_id} не найдена"
            )
        return {"status": "success", "model_id": model_id, "deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении модели {model_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при удалении модели: {str(e)}"
        )


@router.post("/{model_id}/predict", response_model=Dict[str, Any])
async def predict(
    model_id: str,
    data: Dict[str, Any],
    params: Optional[Dict[str, Any]] = None
):
    """Выполняет предсказание с использованием модели."""
    try:
        # Загружаем модель, если она ещё не загружена
        model = await model_manager.get_model(model_id)
        
        # Здесь будет логика предсказания
        # Пока что возвращаем заглушку
        return {
            "status": "success",
            "model_id": model_id,
            "prediction": {"result": "Предсказание не реализовано"},
            "metadata": {
                "model": model_id,
                "params": params or {}
            }
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка при выполнении предсказания: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при выполнении предсказания: {str(e)}"
        )
