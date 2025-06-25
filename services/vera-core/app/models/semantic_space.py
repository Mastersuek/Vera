from typing import List, Dict, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum, auto
import numpy as np
from pydantic import BaseModel, Field, validator
from pathlib import Path
import json
import time
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ObservationPosition(str, Enum):
    INSIDE = "inside"
    OUTSIDE = "outside"
    ABOVE = "above"
    BELOW = "below"
    BESIDE = "beside"
    WITHIN = "within"
    AROUND = "around"

@dataclass
class SemanticMetrics:
    """Performance metrics for semantic operations"""
    distance_calls: int = 0
    neighbor_searches: int = 0
    last_operation_time: float = 0.0
    
    def log_operation(self, operation_name: str, duration: float):
        self.last_operation_time = duration
        logger.debug(f"{operation_name} completed in {duration:.4f}s")

class SemanticPoint(BaseModel):
    """Represents a point in 7D semantic space with optimized storage"""
    coords: np.ndarray = Field(..., max_items=7, min_items=7)
    name: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            np.ndarray: lambda v: v.tolist(),
        }
    
    def __init__(self, **data):
        if 'coords' not in data:
            coords = np.zeros(7, dtype=np.float32)
            for i, dim in enumerate(['x', 'y', 'z', 't', 'o', 'i', 'n']):
                if dim in data:
                    coords[i] = data.pop(dim)
            data['coords'] = coords
        super().__init__(**data)
    
    @property
    def x(self) -> float:
        return float(self.coords[0])
        
    @property
    def y(self) -> float:
        return float(self.coords[1])
        
    @property
    def z(self) -> float:
        return float(self.coords[2])
        
    @property
    def t(self) -> float:
        return float(self.coords[3])
        
    @property
    def o(self) -> ObservationPosition:
        idx = min(int(round(self.coords[4] * (len(ObservationPosition) - 1))), len(ObservationPosition) - 1)
        return list(ObservationPosition)[max(0, idx)]
    
    @property
    def i(self) -> float:
        return float(self.coords[5])
    
    @property
    def n(self) -> int:
        return int(round(self.coords[6]))
    
    def to_vector(self) -> np.ndarray:
        """Convert to numpy array with minimal copying"""
        return self.coords.copy()
    
    def update(self, **kwargs):
        """Efficiently update point attributes"""
        for k, v in kwargs.items():
            if k in ['x', 'y', 'z', 't', 'i']:
                idx = ['x', 'y', 'z', 't', 'i'].index(k)
                self.coords[idx] = float(v)
            elif k == 'o':
                if not isinstance(v, ObservationPosition):
                    v = ObservationPosition(v)
                idx = list(ObservationPosition).index(v)
                self.coords[4] = idx / (len(ObservationPosition) - 1)
            elif k == 'n':
                self.coords[6] = int(v)
            else:
                setattr(self, k, v)
        self.updated_at = time.time()

class SemanticSpace:
    """High-performance semantic space implementation"""
    
    def __init__(self, points: List[SemanticPoint] = None):
        self.points: List[SemanticPoint] = points or []
        self._point_index: Dict[str, int] = {}
        self._point_vectors: Optional[np.ndarray] = None
        self.metrics = SemanticMetrics()
        self._rebuild_index()
    
    def _rebuild_index(self):
        """Rebuild internal indices"""
        self._point_index = {p.name: i for i, p in enumerate(self.points) if p.name}
        if self.points:
            self._point_vectors = np.vstack([p.to_vector() for p in self.points])
    
    def add_point(self, point: SemanticPoint) -> SemanticPoint:
        """Add point with O(1) lookup by name"""
        if point.name in self._point_index:
            idx = self._point_index[point.name]
            self.points[idx] = point
        else:
            self.points.append(point)
            self._point_index[point.name] = len(self.points) - 1
            self._point_vectors = None  # Invalidate cache
        return point
    
    def get_point(self, point_id: str) -> Optional[SemanticPoint]:
        """Get point by name with O(1) lookup"""
        idx = self._point_index.get(point_id)
        return self.points[idx] if idx is not None else None
    
    def calculate_distance(self, p1: Union[SemanticPoint, str], p2: Union[SemanticPoint, str]) -> float:
        """Calculate distance between two points with caching"""
        start_time = time.perf_counter()
        
        if isinstance(p1, str):
            p1 = self.get_point(p1)
        if isinstance(p2, str):
            p2 = self.get_point(p2)
            
        if p1 is None or p2 is None:
            raise ValueError("One or both points not found")
            
        # Use precomputed vectors if available
        v1 = p1.coords
        v2 = p2.coords
        
        # Optimized distance calculation
        diff = v1 - v2
        # Handle circular dimension (observation position)
        diff[4] = min(abs(diff[4]), 1.0 - abs(diff[4]))
        
        # Predefined weights for each dimension
        weights = np.array([1.0, 0.8, 0.9, 0.7, 0.5, 1.2, 0.6], dtype=np.float32)
        
        distance = float(np.sqrt(np.sum((weights * diff) ** 2)))
        
        self.metrics.distance_calls += 1
        self.metrics.log_operation("calculate_distance", time.perf_counter() - start_time)
        
        return distance
    
    def find_nearest_neighbors(self, point: Union[SemanticPoint, str], k: int = 5) -> List[Tuple[SemanticPoint, float]]:
        """Find k nearest neighbors using vectorized operations"""
        start_time = time.perf_counter()
        
        if isinstance(point, str):
            point = self.get_point(point)
            if point is None:
                raise ValueError(f"Point {point} not found")
        
        if not self.points:
            return []
            
        # Use precomputed vectors if available
        if self._point_vectors is None:
            self._point_vectors = np.vstack([p.to_vector() for p in self.points])
            
        point_vec = point.to_vector().reshape(1, -1)
        
        # Vectorized distance calculation
        diff = self._point_vectors - point_vec
        diff[:, 4] = np.minimum(np.abs(diff[:, 4]), 1.0 - np.abs(diff[:, 4]))
        weights = np.array([1.0, 0.8, 0.9, 0.7, 0.5, 1.2, 0.6], dtype=np.float32)
        distances = np.sqrt(np.sum((weights * diff) ** 2, axis=1))
        
        # Get indices of k smallest distances (excluding self if present)
        point_indices = np.arange(len(self.points))
        if point in self.points:
            point_idx = self.points.index(point)
            mask = point_indices != point_idx
            distances = distances[mask]
            point_indices = point_indices[mask]
            
        k = min(k, len(point_indices))
        if k <= 0:
            return []
            
        top_k_indices = np.argpartition(distances, k)[:k]
        top_k_distances = distances[top_k_indices]
        
        # Sort by distance
        sorted_indices = np.argsort(top_k_distances)
        result = [
            (self.points[point_indices[i]], float(top_k_distances[i]))
            for i in sorted_indices
        ]
        
        self.metrics.neighbor_searches += 1
        self.metrics.log_operation(f"find_nearest_neighbors (k={k})", time.perf_counter() - start_time)
        
        return result
    
    def batch_calculate_distances(self, point_pairs: List[Tuple[str, str]]) -> List[float]:
        """Calculate distances for multiple point pairs in parallel"""
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self.calculate_distance, p1, p2)
                for p1, p2 in point_pairs
            ]
            return [f.result() for f in as_completed(futures)]
    
    def save_to_file(self, filepath: Union[str, Path]):
        """Save space to file efficiently"""
        data = {
            'points': [p.dict() for p in self.points],
            'metrics': {
                'distance_calls': self.metrics.distance_calls,
                'neighbor_searches': self.metrics.neighbor_searches,
            }
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: Union[str, Path]) -> 'SemanticSpace':
        """Load space from file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        space = cls()
        for point_data in data['points']:
            if 'coords' in point_data:
                point_data['coords'] = np.array(point_data['coords'], dtype=np.float32)
            space.add_point(SemanticPoint(**point_data))
        
        if 'metrics' in data:
            space.metrics.distance_calls = data['metrics'].get('distance_calls', 0)
            space.metrics.neighbor_searches = data['metrics'].get('neighbor_searches', 0)
            
        return space
    
    def __len__(self) -> int:
        return len(self.points)
    
    def __contains__(self, point: Union[SemanticPoint, str]) -> bool:
        if isinstance(point, SemanticPoint):
            return point in self.points
        return point in self._point_index
