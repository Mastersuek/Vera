"""
Модуль для управления моделями ИИ.

Содержит классы для загрузки, кэширования и управления предобученными моделями.
"""
import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime

import torch
from loguru import logger
import redis
from rq import Queue
from pydantic import BaseModel, Field

from .config import settings


class ModelInfo(BaseModel):
    """Информация о модели."""
    model_id: str = Field(..., description="Идентификатор модели")
    name: str = Field(..., description="Название модели")
    description: str = Field("", description="Описание модели")
    version: str = Field("latest", description="Версия модели")
    framework: str = Field("pytorch", description="Фреймворк модели (pytorch, tensorflow, etc.)")
    size_mb: float = Field(0.0, description="Размер модели в мегабайтах")
    loaded: bool = Field(False, description="Загружена ли модель в память")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Параметры модели")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Дата создания записи")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Дата обновления записи")

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует модель в словарь."""
        result = self.dict()
        result["created_at"] = self.created_at.isoformat()
        result["updated_at"] = self.updated_at.isoformat()
        return result


class ModelManager:
    """Менеджер для управления моделями ИИ."""
    
    def __init__(self, models_dir: Path, redis_conn: redis.Redis, rq_queue: Queue):
        """Инициализация менеджера моделей.
        
        Args:
            models_dir: Директория для хранения моделей
            redis_conn: Подключение к Redis
            rq_queue: Очередь задач RQ
        """
        self.models_dir = models_dir
        self.redis = redis_conn
        self.rq_queue = rq_queue
        self._models: Dict[str, Any] = {}
        self._models_meta: Dict[str, ModelInfo] = {}
        self._model_locks: Dict[str, asyncio.Lock] = {}
        
        # Создаем директорию для моделей, если её нет
        self.models_dir.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Инициализация менеджера моделей."""
        logger.info(f"Инициализация ModelManager в директории {self.models_dir}")
        await self._load_models_metadata()
        
        # Загружаем модели по умолчанию
        for model_id in settings.DEFAULT_MODELS:
            if model_id not in self._models_meta:
                await self.download_model(model_id)
    
    async def _load_models_metadata(self) -> None:
        """Загружает метаданные моделей из Redis."""
        try:
            # Загружаем метаданные из Redis
            for key in self.redis.keys("model:*"):
                model_id = key.decode().split(":", 1)[1]
                model_data = self.redis.get(key)
                if model_data:
                    model_info = ModelInfo.parse_raw(model_data)
                    self._models_meta[model_id] = model_info
            
            logger.info(f"Загружены метаданные для {len(self._models_meta)} моделей")
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке метаданных моделей: {str(e)}")
    
    async def _save_model_metadata(self, model_info: ModelInfo) -> None:
        """Сохраняет метаданные модели в Redis.
        
        Args:
            model_info: Информация о модели
        """
        try:
            model_info.updated_at = datetime.utcnow()
            self.redis.set(f"model:{model_info.model_id}", model_info.json())
            self._models_meta[model_info.model_id] = model_info
        except Exception as e:
            logger.error(f"Ошибка при сохранении метаданных модели {model_info.model_id}: {str(e)}")
    
    async def download_model(self, model_id: str, **kwargs) -> ModelInfo:
        """Загружает модель из репозитория.
        
        Args:
            model_id: Идентификатор модели (например, 'sentence-transformers/all-mpnet-base-v2')
            **kwargs: Дополнительные параметры загрузки
            
        Returns:
            ModelInfo: Информация о загруженной модели
        """
        if model_id in self._models_meta:
            logger.info(f"Модель {model_id} уже загружена")
            return self._models_meta[model_id]
        
        # Создаем блокировку для этой модели, если её ещё нет
        if model_id not in self._model_locks:
            self._model_locks[model_id] = asyncio.Lock()
        
        async with self._model_locks[model_id]:
            # Двойная проверка после получения блокировки
            if model_id in self._models_meta:
                return self._models_meta[model_id]
            
            logger.info(f"Начало загрузки модели {model_id}")
            
            try:
                # Создаем информацию о модели
                model_info = ModelInfo(
                    model_id=model_id,
                    name=model_id.split('/')[-1],
                    description=f"Модель {model_id} из Hugging Face Hub",
                    parameters=kwargs
                )
                
                # Сохраняем метаданные
                await self._save_model_metadata(model_info)
                
                # Помещаем задачу на загрузку в очередь RQ
                job = self.rq_queue.enqueue(
                    "ai_agent.tasks.download_model_task",
                    model_id=model_id,
                    model_dir=str(self.models_dir / model_id.replace('/', '_')),
                    **kwargs
                )
                
                logger.info(f"Задача на загрузку модели {model_id} поставлена в очередь (ID: {job.id})")
                
                return model_info
                
            except Exception as e:
                logger.error(f"Ошибка при загрузке модели {model_id}: {str(e)}")
                raise
    
    async def get_model(self, model_id: str) -> Any:
        """Возвращает загруженную модель.
        
        Args:
            model_id: Идентификатор модели
            
        Returns:
            Загруженная модель
        """
        if model_id not in self._models_meta:
            raise ValueError(f"Модель {model_id} не найдена")
        
        # Если модель уже загружена в память, возвращаем её
        if model_id in self._models:
            return self._models[model_id]
        
        # Иначе загружаем модель
        model_info = self._models_meta[model_id]
        
        try:
            # Здесь будет загрузка модели в память
            # Пока что возвращаем заглушку
            self._models[model_id] = {"model_id": model_id, "loaded": True}
            model_info.loaded = True
            await self._save_model_metadata(model_info)
            
            return self._models[model_id]
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели {model_id} в память: {str(e)}")
            raise
    
    def list_models(self) -> List[Dict[str, Any]]:
        """Возвращает список всех доступных моделей."""
        return [model.to_dict() for model in self._models_meta.values()]
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Возвращает информацию о модели."""
        if model_id in self._models_meta:
            return self._models_meta[model_id].to_dict()
        return None
    
    async def unload_model(self, model_id: str) -> bool:
        """Выгружает модель из памяти."""
        if model_id in self._models:
            # Здесь должна быть логика выгрузки модели из памяти
            del self._models[model_id]
            
            if model_id in self._models_meta:
                model_info = self._models_meta[model_id]
                model_info.loaded = False
                await self._save_model_metadata(model_info)
            
            logger.info(f"Модель {model_id} выгружена из памяти")
            return True
        return False
    
    async def delete_model(self, model_id: str) -> bool:
        """Удаляет модель из системы."""
        if model_id in self._models_meta:
            # Выгружаем модель из памяти, если она загружена
            await self.unload_model(model_id)
            
            # Удаляем модель из Redis
            self.redis.delete(f"model:{model_id}")
            
            # Удаляем модель из кэша метаданных
            del self._models_meta[model_id]
            
            # Удаляем файлы модели
            model_dir = self.models_dir / model_id.replace('/', '_')
            if model_dir.exists():
                import shutil
                shutil.rmtree(model_dir)
            
            logger.info(f"Модель {model_id} удалена")
            return True
        return False
