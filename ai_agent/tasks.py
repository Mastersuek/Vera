"""
Модуль для фоновых задач агента управления моделями ИИ.

Содержит задачи, которые выполняются асинхронно через RQ (Redis Queue).
"""
import os
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from loguru import logger
import torch
from huggingface_hub import snapshot_download, hf_hub_download
from rq import get_current_job

from .config import settings


def get_job_progress() -> float:
    """Возвращает текущий прогресс задачи."""
    job = get_current_job()
    if not job:
        return 0.0
    
    meta = job.meta or {}
    return meta.get('progress', 0.0)


def update_job_progress(progress: float, message: str = "") -> None:
    """Обновляет прогресс выполнения задачи.
    
    Args:
        progress: Текущий прогресс от 0.0 до 1.0
        message: Опциональное сообщение о статусе
    """
    job = get_current_job()
    if not job:
        return
    
    meta = job.meta or {}
    meta['progress'] = max(0.0, min(1.0, progress))
    if message:
        meta['message'] = message
    
    job.meta = meta
    job.save_meta()


def download_model_task(
    model_id: str,
    model_dir: str,
    token: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Задача для загрузки модели из Hugging Face Hub.
    
    Args:
        model_id: Идентификатор модели в Hugging Face Hub
        model_dir: Директория для сохранения модели
        token: Токен аутентификации для Hugging Face Hub
        **kwargs: Дополнительные параметры загрузки
        
    Returns:
        Словарь с информацией о загруженной модели
    """
    start_time = time.time()
    update_job_progress(0.05, f"Начало загрузки модели {model_id}")
    
    try:
        model_dir_path = Path(model_dir)
        model_dir_path.mkdir(parents=True, exist_ok=True)
        
        # Скачиваем модель из Hugging Face Hub
        update_job_progress(0.1, f"Подготовка к загрузке {model_id}")
        
        # Проверяем, есть ли модель в кэше
        cache_dir = str(model_dir_path / ".cache")
        os.makedirs(cache_dir, exist_ok=True)
        
        # Используем snapshot_download для полной загрузки репозитория
        # или hf_hub_download для конкретных файлов
        update_job_progress(0.2, f"Загрузка модели {model_id} из Hugging Face Hub")
        
        # Скачиваем репозиторий с моделями
        snapshot_path = snapshot_download(
            repo_id=model_id,
            cache_dir=cache_dir,
            local_dir=str(model_dir_path),
            local_dir_use_symlinks=True,
            token=token,
            **kwargs
        )
        
        # Получаем информацию о размере модели
        total_size = sum(
            f.stat().st_size 
            for f in model_dir_path.glob('**/*') 
            if f.is_file()
        ) / (1024 * 1024)  # в МБ
        
        # Проверяем наличие файлов конфигурации
        has_config = any(
            f.name in ('config.json', 'pytorch_model.bin', 'model.safetensors')
            for f in model_dir_path.iterdir()
        )
        
        if not has_config:
            logger.warning(f"Модель {model_id} не содержит стандартных файлов конфигурации")
        
        update_job_progress(0.9, f"Завершение загрузки {model_id}")
        
        # Возвращаем информацию о загруженной модели
        result = {
            "status": "success",
            "model_id": model_id,
            "path": str(model_dir_path.absolute()),
            "size_mb": round(total_size, 2),
            "files": [str(p.relative_to(model_dir_path)) 
                     for p in model_dir_path.rglob('*') if p.is_file()],
            "time_sec": round(time.time() - start_time, 2),
            "device": str(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu'),
        }
        
        update_job_progress(1.0, f"Модель {model_id} успешно загружена")
        return result
        
    except Exception as e:
        error_msg = f"Ошибка при загрузке модели {model_id}: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg) from e


def load_model_task(model_id: str, model_path: str, device: str = None) -> Dict[str, Any]:
    """Задача для загрузки модели в память.
    
    Args:
        model_id: Идентификатор модели
        model_path: Путь к загруженной модели
        device: Устройство для загрузки модели (cpu, cuda, cuda:0 и т.д.)
        
    Returns:
        Словарь с информацией о загруженной модели
    """
    try:
        update_job_progress(0.1, f"Подготовка к загрузке модели {model_id} в память")
        
        # Определяем устройство
        if device is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        # Проверяем наличие модели
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Модель {model_id} не найдена по пути {model_path}")
        
        # Здесь будет логика загрузки конкретной модели
        # В этом примере просто имитируем загрузку
        update_job_progress(0.5, f"Загрузка модели {model_id} на устройство {device}")
        
        # Имитация загрузки
        time.sleep(2)
        
        # Возвращаем информацию о загруженной модели
        result = {
            "status": "success",
            "model_id": model_id,
            "device": device,
            "loaded_layers": 0,  # Здесь будет реальное количество загруженных слоев
            "memory_usage_mb": 0,  # Здесь будет реальное использование памяти
        }
        
        update_job_progress(1.0, f"Модель {model_id} успешно загружена в память")
        return result
        
    except Exception as e:
        error_msg = f"Ошибка при загрузке модели {model_id} в память: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg) from e
