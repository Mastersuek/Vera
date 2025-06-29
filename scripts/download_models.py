#!/usr/bin/env python3
"""
Скрипт для загрузки предварительно обученных моделей ИИ.

Этот скрипт загружает модели из Hugging Face Hub в указанную директорию.
"""
import os
import logging
from pathlib import Path
from typing import List, Optional

from huggingface_hub import snapshot_download, HfApi, HfFolder
from loguru import logger
from tqdm import tqdm

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logger.bind(name="model_downloader")

# Список моделей по умолчанию
DEFAULT_MODELS = [
    "sentence-transformers/all-mpnet-base-v2",  # Универсальная модель для эмбеддингов
    "facebook/bart-large-mnli",  # Модель для классификации
    "bigscience/bloom-560m",  # Генеративная модель
]


def download_model(
    model_id: str,
    cache_dir: Optional[str] = None,
    token: Optional[str] = None,
    revision: Optional[str] = None,
) -> str:
    """
    Загружает модель из Hugging Face Hub.

    Args:
        model_id: Идентификатор модели в формате 'org/model-name'
        cache_dir: Директория для кэширования моделей
        token: Токен для доступа к приватным репозиториям
        revision: Версия модели (ветка, тег или хеш коммита)

    Returns:
        str: Путь к загруженной модели
    """
    try:
        logger.info(f"Загрузка модели: {model_id}")
        
        # Загружаем модель с помощью huggingface_hub
        model_path = snapshot_download(
            repo_id=model_id,
            cache_dir=cache_dir,
            token=token,
            revision=revision,
            ignore_patterns=["*.bin", "*.h5", "*.ot", "*.msgpack"],
        )
        
        logger.success(f"Модель {model_id} успешно загружена в {model_path}")
        return model_path
    except Exception as e:
        logger.error(f"Ошибка при загрузке модели {model_id}: {str(e)}")
        raise


def get_model_info(model_id: str, token: Optional[str] = None) -> dict:
    """Получает информацию о модели из Hugging Face Hub."""
    try:
        api = HfApi(token=token)
        model_info = api.model_info(model_id)
        return {
            "id": model_info.modelId,
            "last_modified": model_info.lastModified,
            "tags": model_info.tags,
            "pipeline_tag": model_info.pipeline_tag,
            "downloads": model_info.downloads,
        }
    except Exception as e:
        logger.error(f"Не удалось получить информацию о модели {model_id}: {str(e)}")
        return {}


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Загрузчик моделей ИИ")
    parser.add_argument(
        "--models",
        nargs="+",
        default=DEFAULT_MODELS,
        help="Список моделей для загрузки",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default=os.getenv("MODEL_CACHE_DIR", "./models"),
        help="Директория для кэширования моделей",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=os.getenv("HF_TOKEN"),
        help="Токен для доступа к приватным репозиториям",
    )
    
    args = parser.parse_args()
    
    # Создаем директорию для кэша, если её нет
    cache_dir = Path(args.cache_dir).absolute()
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Используется директория для кэша: {cache_dir}")
    
    # Загружаем модели
    for model_id in tqdm(args.models, desc="Загрузка моделей"):
        try:
            model_info = get_model_info(model_id, args.token)
            logger.info(f"Информация о модели {model_id}: {model_info}")
            
            model_path = download_model(
                model_id=model_id,
                cache_dir=str(cache_dir),
                token=args.token,
            )
            logger.info(f"Модель сохранена в: {model_path}")
            
        except Exception as e:
            logger.error(f"Не удалось загрузить модель {model_id}: {str(e)}")
            continue
    
    logger.info("Завершена загрузка всех моделей")


if __name__ == "__main__":
    main()
