#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Демонстрация работы с семантическим пространством, визуализацией и системой самовосстановления.

Этот пример показывает:
1. Создание и настройку семантического пространства
2. Добавление точек в пространство
3. Выполнение операций над точками
4. Визуализацию результатов
5. Интеграцию с системой самовосстановления
"""

import os
import sys
import time
import random
import numpy as np
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
project_root = str(Path(__file__).parent.parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.models.semantic_space import SemanticPoint, SemanticSpace
from app.models.semantic_operations import SemanticOperations, DistributedSemanticProcessor
from app.visualization.semantic_visualizer import SemanticVisualizer
from app.core.self_healing import SelfHealingSystem, create_service_supervisor
from app.core.logging import get_logger

# Настраиваем логирование
logger = get_logger(__name__)

def generate_sample_points(n: int = 100, dim: int = 7) -> list:
    """Генерирует тестовые точки для демонстрации"""
    categories = ["животные", "растения", "техника", "города", "наука"]
    points = []
    
    for i in range(n):
        # Случайные координаты в 7D пространстве
        coordinates = np.random.normal(0, 1, dim).tolist()
        category = random.choice(categories)
        
        # Создаем точку с осмысленным именем и описанием
        point = SemanticPoint(
            name=f"{category}_{i}",
            coordinates=coordinates,
            metadata={
                "category": category,
                "source": "demo",
                "dimensions": dim
            },
            description=f"Тестовая точка {i} в категории {category}"
        )
        points.append(point)
    
    return points

def demo_semantic_operations():
    """Демонстрация работы с семантическим пространством"""
    logger.info("Инициализация семантического пространства...")
    space = SemanticSpace(dimensions=7)
    
    # Генерируем тестовые точки
    logger.info("Генерация тестовых точек...")
    points = generate_sample_points(100, 7)
    
    # Добавляем точки в пространство
    for point in points:
        space.add_point(point)
    
    logger.info(f"Добавлено {len(space.points)} точек в пространство")
    
    # Создаем экземпляр операций
    operations = SemanticOperations(space)
    
    # Пример 1: Находим похожие точки
    if len(space.points) > 5:
        query_point = space.points[0]
        similar = space.find_similar_points(query_point, top_k=3)
        logger.info(f"\nНаиболее похожие на '{query_point.name}':")
        for point, similarity in similar:
            logger.info(f"  - {point.name} (сходство: {similarity:.3f})")
    
    # Пример 2: Вычисляем матрицу сходства
    logger.info("\nВычисление матрицы сходства...")
    similarity_matrix = operations.calculate_similarity_matrix()
    logger.info(f"Размерность матрицы сходства: {similarity_matrix.shape}")
    
    # Пример 3: Кластеризация
    logger.info("\nКластеризация точек...")
    n_clusters = min(5, len(space.points) // 2)
    if n_clusters > 1:
        clusters = operations.find_semantic_clusters(n_clusters=n_clusters)
        for cluster_id, cluster_points in clusters.items():
            logger.info(f"Кластер {cluster_id}: {len(cluster_points)} точек")
    
    # Пример 4: Визуализация
    logger.info("\nСоздание визуализаций...")
    visualizer = SemanticVisualizer(space)
    
    # Создаем директорию для результатов, если её нет
    output_dir = Path("demo_results")
    output_dir.mkdir(exist_ok=True)
    
    # 2D визуализация
    fig_2d = visualizer.plot_2d_scatter(
        method='umap',
        color_by='cluster',
        title="2D визуализация семантического пространства (UMAP)",
        save_path=output_dir / "semantic_space_2d.html",
        show=False
    )
    
    # 3D визуализация, если точек достаточно
    if len(space.points) >= 3:
        fig_3d = visualizer.plot_3d_scatter(
            method='pca',
            color_by='cluster',
            title="3D визуализация семантического пространства (PCA)",
            save_path=output_dir / "semantic_space_3d.html",
            show=False
        )
    
    # Сетевая визуализация
    if len(space.points) >= 10:
        network_fig = visualizer.plot_semantic_network(
            max_edges=50,
            threshold=0.7,
            title="Семантическая сеть",
            save_path=output_dir / "semantic_network.html",
            show=False
        )
    
    logger.info(f"\nВизуализации сохранены в директорию: {output_dir.absolute()}")
    
    # Пример 5: Распределённая обработка
    logger.info("\nДемонстрация распределённой обработки...")
    processor = DistributedSemanticProcessor(space)
    
    # Функция для обработки точки (пример)
    def process_point(point: SemanticPoint) -> dict:
        # Имитация ресурсоёмкой операции
        time.sleep(0.01)
        return {
            'name': point.name,
            'norm': np.linalg.norm(point.to_vector()),
            'category': point.metadata.get('category', 'unknown')
        }
    
    # Обработка точек в несколько потоков
    results = processor.process_in_batches(process_point, batch_size=10)
    logger.info(f"Обработано {len(results)} точек в параллельном режиме")
    
    # Пример 6: Сохранение и загрузка состояния
    state_file = output_dir / "semantic_space_state.json"
    space.save_to_file(state_file)
    logger.info(f"Состояние семантического пространства сохранено в {state_file}")
    
    # Загрузка состояния в новое пространство
    new_space = SemanticSpace()
    new_space.load_from_file(state_file)
    logger.info(f"Загружено пространство с {len(new_space.points)} точками")
    
    return space

def demo_self_healing():
    """Демонстрация работы системы самовосстановления"""
    logger.info("\n" + "="*50)
    logger.info("Демонстрация системы самовосстановления")
    logger.info("="*50)
    
    # Альтернативный вариант с супервизором
    def service_function():
        """Функция, представляющая наш сервис"""
        logger.info("Сервис запущен")
        try:
            while True:
                # Имитация работы сервиса
                time.sleep(1)
                
                # Иногда имитируем ошибку
                if random.random() < 0.1:  # 10% вероятность ошибки для демонстрации
                    logger.warning("Имитация ошибки в работе сервиса...")
                    raise RuntimeError("Имитация критической ошибки")
                    
        except KeyboardInterrupt:
            logger.info("Сервис завершает работу по запросу пользователя")
            return 0
    
    # Создаем и запускаем супервизор
    supervisor = create_service_supervisor("semantic_service", service_function, max_restarts=3)
    supervisor.start()
    
    try:
        # Ждем завершения супервизора (в реальном приложении можно делать что-то ещё)
        while supervisor.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Получен сигнал завершения, останавливаем супервизор...")
        supervisor.stop()
    
    supervisor.join()
    logger.info("Демонстрация завершена")

def main():
    """Основная функция демонстрации"""
    try:
        # Демонстрация работы с семантическим пространством
        space = demo_semantic_operations()
        
        # Демонстрация системы самовосстановления
        demo_self_healing()
        
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
