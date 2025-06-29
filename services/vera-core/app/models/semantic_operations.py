import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import json
import logging
from functools import partial

from .semantic_space import SemanticPoint, SemanticSpace
from ..core.logging import get_logger

logger = get_logger(__name__)


class SemanticOperations:
    """Класс для расширенных математических операций с семантическим пространством"""
    
    def __init__(self, semantic_space: SemanticSpace):
        self.space = semantic_space
    
    def calculate_similarity_matrix(self) -> np.ndarray:
        """
        Вычисляет матрицу попарных сходств между всеми точками пространства.
        Возвращает симметричную матрицу размером NxN, где N - количество точек.
        """
        points = self.space.points
        n = len(points)
        if n == 0:
            return np.array([])
            
        # Получаем все векторы за один раз
        vectors = np.array([p.to_vector() for p in points])
        
        # Нормализуем векторы для косинусного сходства
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10  # Избегаем деления на ноль
        normalized = vectors / norms
        
        # Матрица косинусных сходств
        similarity_matrix = np.dot(normalized, normalized.T)
        
        # Округляем для численной стабильности
        similarity_matrix = np.clip(similarity_matrix, -1.0, 1.0)
        
        return similarity_matrix
    
    def find_semantic_clusters(self, n_clusters: int, max_iters: int = 100) -> Dict[int, List[SemanticPoint]]:
        """
        Кластеризует точки семантического пространства с помощью алгоритма k-средних.
        Возвращает словарь, где ключи - это номера кластеров, а значения - списки точек.
        """
        from sklearn.cluster import KMeans
        
        if len(self.space.points) < n_clusters:
            raise ValueError(f"Недостаточно точек ({len(self.space.points)}) для {n_clusters} кластеров")
        
        # Получаем векторы всех точек
        vectors = np.array([p.to_vector() for p in self.space.points])
        
        # Применяем K-means
        kmeans = KMeans(n_clusters=n_clusters, max_iter=max_iters, n_init=10, random_state=42)
        clusters = kmeans.fit_predict(vectors)
        
        # Группируем точки по кластерам
        result = {i: [] for i in range(n_clusters)}
        for point, cluster_id in zip(self.space.points, clusters):
            result[cluster_id].append(point)
            
        return result
    
    def project_to_lower_dimension(self, target_dim: int = 2, method: str = 'pca') -> np.ndarray:
        """
        Проецирует точки в пространство меньшей размерности.
        Поддерживаемые методы: 'pca', 'tsne', 'umap'.
        Возвращает массив формы (n_points, target_dim).
        """
        if len(self.space.points) == 0:
            return np.array([])
            
        vectors = np.array([p.to_vector() for p in self.space.points])
        
        if method == 'pca':
            from sklearn.decomposition import PCA
            reducer = PCA(n_components=target_dim)
        elif method == 'tsne':
            from sklearn.manifold import TSNE
            reducer = TSNE(n_components=target_dim, random_state=42)
        elif method == 'umap':
            from umap import UMAP
            reducer = UMAP(n_components=target_dim, random_state=42)
        else:
            raise ValueError(f"Неподдерживаемый метод проекции: {method}")
        
        return reducer.fit_transform(vectors)
    
    def batch_process_points(self, process_func, batch_size: int = 1000, **kwargs) -> List[Any]:
        """
        Применяет функцию process_func к точкам пакетами.
        Полезно для обработки больших наборов данных.
        """
        points = self.space.points
        results = []
        
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            batch_results = [process_func(point, **kwargs) for point in batch]
            results.extend(batch_results)
            
        return results
    
    def parallel_distance_calculation(self, point_pairs: List[Tuple[str, str]], n_workers: int = None) -> List[float]:
        """
        Параллельный расчёт расстояний между парами точек.
        Возвращает список расстояний в том же порядке, что и пары.
        """
        if not point_pairs:
            return []
            
        # Создаем словарь для быстрого доступа к точкам
        point_dict = {p.name: p for p in self.space.points if p.name is not None}
        
        # Проверяем, что все точки существуют
        missing = []
        for i, (id1, id2) in enumerate(point_pairs):
            if id1 not in point_dict or id2 not in point_dict:
                missing.append((i, id1 if id1 not in point_dict else id2))
        
        if missing:
            missing_str = ", ".join(f"пара {i}: точка '{id}' не найдена" for i, id in missing[:5])
            if len(missing) > 5:
                missing_str += f" ... и ещё {len(missing) - 5} пар"
            raise ValueError(f"Не найдены точки: {missing_str}")
        
        # Функция для расчёта расстояния между парой точек
        def calculate_distance(pair):
            id1, id2 = pair
            p1 = point_dict[id1]
            p2 = point_dict[id2]
            return self.space.calculate_distance(p1, p2)
        
        # Используем ProcessPoolExecutor для параллельных вычислений
        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            distances = list(executor.map(calculate_distance, point_pairs))
            
        return distances
    
    def semantic_interpolation(self, point1_id: str, point2_id: str, steps: int = 10) -> List[Dict[str, Any]]:
        """
        Выполняет семантическую интерполяцию между двумя точками.
        Возвращает список словарей с промежуточными точками и их метаданными.
        """
        point1 = next((p for p in self.space.points if p.name == point1_id), None)
        point2 = next((p for p in self.space.points if p.name == point2_id), None)
        
        if not point1 or not point2:
            raise ValueError("Одна или обе точки не найдены")
            
        v1 = point1.to_vector()
        v2 = point2.to_vector()
        
        result = []
        for alpha in np.linspace(0, 1, steps):
            # Линейная интерполяция векторов
            interp_vector = v1 * (1 - alpha) + v2 * alpha
            
            # Создаем новую точку с интерполированными координатами
            interp_point = SemanticPoint.from_vector(interp_vector)
            interp_point.name = f"{point1_id}_to_{point2_id}_{alpha:.2f}"
            interp_point.description = f"Интерполяция между {point1_id} и {point2_id} (шаг {alpha:.2f})"
            
            result.append({
                'point': interp_point,
                'alpha': alpha,
                'distance_to_start': float(np.linalg.norm(interp_vector - v1)),
                'distance_to_end': float(np.linalg.norm(interp_vector - v2))
            })
            
        return result
    
    def semantic_centroid(self, point_ids: List[str]) -> SemanticPoint:
        """
        Вычисляет центроид (среднюю точку) для набора точек.
        Возвращает новую точку, представляющую центроид.
        """
        if not point_ids:
            raise ValueError("Список идентификаторов точек не может быть пустым")
            
        points = [p for p in self.space.points if p.name in point_ids]
        if len(points) != len(point_ids):
            found_ids = {p.name for p in points}
            missing = set(point_ids) - found_ids
            raise ValueError(f"Не найдены точки: {', '.join(missing)}")
            
        # Вычисляем средний вектор
        vectors = np.array([p.to_vector() for p in points])
        centroid_vector = np.mean(vectors, axis=0)
        
        # Создаем новую точку-центроид
        centroid = SemanticPoint.from_vector(centroid_vector)
        centroid.name = f"centroid_of_{'_'.join(point_ids[:3])}{'_more' if len(point_ids) > 3 else ''}"
        centroid.description = f"Центроид точек: {', '.join(point_ids[:5])}{'...' if len(point_ids) > 5 else ''}"
        
        return centroid


class DistributedSemanticProcessor:
    """Класс для распределённой обработки семантического пространства"""
    
    def __init__(self, space: SemanticSpace, n_workers: int = None):
        self.space = space
        self.n_workers = n_workers or (os.cpu_count() - 1 if os.cpu_count() else 1)
    
    def process_in_batches(self, process_func, batch_size: int = 1000, **kwargs):
        """Обрабатывает точки пакетами с использованием пула процессов"""
        points = self.space.points
        results = []
        
        with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
            # Делим точки на пакеты
            batches = [points[i:i + batch_size] for i in range(0, len(points), batch_size)]
            
            # Создаем частично примененную функцию с аргументами
            partial_func = partial(self._process_batch, process_func=process_func, **kwargs)
            
            # Запускаем обработку пакетов параллельно
            futures = [executor.submit(partial_func, batch) for batch in batches]
            
            # Собираем результаты
            for future in as_completed(futures):
                try:
                    batch_results = future.result()
                    results.extend(batch_results)
                except Exception as e:
                    logger.error(f"Ошибка при обработке пакета: {e}")
                    raise
        
        return results
    
    def _process_batch(self, batch, process_func, **kwargs):
        """Обрабатывает один пакет точек"""
        return [process_func(point, **kwargs) for point in batch]
    
    def save_state(self, filepath: Union[str, Path]):
        """Сохраняет состояние процессора в файл"""
        state = {
            'n_workers': self.n_workers,
            'space_size': len(self.space)
        }
        
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
    
    @classmethod
    def load_state(cls, space: SemanticSpace, filepath: Union[str, Path]) -> 'DistributedSemanticProcessor':
        """Загружает состояние процессора из файла"""
        with open(filepath, 'r') as f:
            state = json.load(f)
            
        processor = cls(space, n_workers=state.get('n_workers'))
        return processor
