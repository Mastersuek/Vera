#!/usr/bin/env python3
"""
Worker для обработки фоновых задач с использованием RQ (Redis Queue).

Этот скрипт запускает воркер, который обрабатывает задачи из очереди Redis.
"""
import os
import logging
import argparse
from pathlib import Path
from rq import Worker, Queue, Connection
from redis import Redis
from loguru import logger

from .config import settings

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logger.bind(name="ai_agent_worker")

def parse_args():
    """Разбор аргументов командной строки."""
    parser = argparse.ArgumentParser(description='Worker для обработки фоновых задач')
    parser.add_argument('--queues', '-q', nargs='+', default=['default'],
                      help='Очереди для прослушивания (по умолчанию: default)')
    parser.add_argument('--name', '-n', default=None,
                      help='Имя воркера')
    parser.add_argument('--burst', '-b', action='store_true',
                      help='Режим burst (завершить работу после обработки всех задач)')
    parser.add_argument('--with-scheduler', '-s', action='store_true',
                      help='Запустить планировщик RQ Scheduler')
    return parser.parse_args()

def run_worker(queues, name=None, burst=False, with_scheduler=False):
    """Запускает воркер для обработки задач.
    
    Args:
        queues: Список имен очередей для прослушивания
        name: Имя воркера
        burst: Режим burst (завершить работу после обработки всех задач)
        with_scheduler: Запустить планировщик RQ Scheduler
    """
    # Подключаемся к Redis
    redis_conn = Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD or None,
        db=settings.REDIS_DB
    )
    
    # Создаем объекты очередей
    rq_queues = [Queue(queue, connection=redis_conn) for queue in queues]
    
    # Запускаем воркер
    with Connection(connection=redis_conn):
        worker = Worker(
            rq_queues,
            name=name,
            default_worker_ttl=600,  # Время жизни воркера (10 минут)
            job_monitoring_interval=5.0,  # Интервал мониторинга задач (сек)
            disable_default_exception_handler=True,  # Используем свой обработчик исключений
        )
        
        # Настраиваем обработчики событий
        worker.push_exc_handler(handle_failed_job)
        
        logger.info(f"Запуск воркера {worker.name} для очередей: {', '.join(queues)}")
        
        # Запускаем воркер
        worker.work(burst=burst, with_scheduler=with_scheduler)

def handle_failed_job(job, exc_type, exc_value, traceback):
    """Обработчик неудачных задач."""
    logger.error(f"Ошибка при выполнении задачи {job.id}:")
    logger.error(f"Тип: {exc_type.__name__}")
    logger.error(f"Сообщение: {str(exc_value)}")
    logger.error(f"Аргументы: {job.kwargs}")
    
    # Пометка задачи как неудачной
    job.meta.setdefault('errors', []).append({
        'type': exc_type.__name__,
        'message': str(exc_value),
        'traceback': traceback.format_exc() if traceback else None
    })
    job.save_meta()
    
    # Возвращаем True, чтобы пометить задачу как обработанную
    return True

def main():
    """Основная функция."""
    args = parse_args()
    
    # Запускаем воркер
    run_worker(
        queues=args.queues,
        name=args.name,
        burst=args.burst,
        with_scheduler=args.with_scheduler
    )

if __name__ == "__main__":
    main()
