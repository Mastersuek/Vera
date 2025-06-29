from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks, status
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
import numpy as np
import logging
from pathlib import Path
import json
import time

from app.models.semantic_space import SemanticPoint, SemanticSpace, ObservationPosition, SemanticMetrics
from app.core.config import settings
from app.core.security import get_current_active_user

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory storage with optimized indexing
semantic_space = SemanticSpace()

# Request/Response Models
class PointCreate(BaseModel):
    x: float = Field(..., ge=-1.0, le=1.0)
    y: float = Field(..., ge=-1.0, le=1.0)
    z: float = Field(..., ge=-1.0, le=1.0)
    t: float = Field(..., ge=-1.0, le=1.0)
    o: ObservationPosition
    i: float = Field(..., ge=0.0, le=1.0)
    n: int = Field(..., ge=0)
    name: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class PointUpdate(BaseModel):
    x: Optional[float] = Field(None, ge=-1.0, le=1.0)
    y: Optional[float] = Field(None, ge=-1.0, le=1.0)
    z: Optional[float] = Field(None, ge=-1.0, le=1.0)
    t: Optional[float] = Field(None, ge=-1.0, le=1.0)
    o: Optional[ObservationPosition] = None
    i: Optional[float] = Field(None, ge=0.0, le=1.0)
    n: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class PointResponse(SemanticPoint):
    class Config:
        json_encoders = {
            np.ndarray: lambda v: v.tolist(),
        }

class DistanceRequest(BaseModel):
    point1_id: str
    point2_id: str

class DistanceResponse(BaseModel):
    distance: float
    uncertainty: Optional[float] = None
    processing_time_ms: float

class NeighborsRequest(BaseModel):
    point_id: str
    k: int = Field(5, ge=1, le=100)

class NeighborResponse(BaseModel):
    point: PointResponse
    distance: float
    uncertainty: Optional[float] = None

class BulkImportResponse(BaseModel):
    imported: int
    skipped: int
    errors: List[Dict[str, Any]]
    processing_time_ms: float

class SpaceMetricsResponse(SemanticMetrics):
    total_points: int
    dimensions: int = 7
    size_bytes: int
    last_updated: float

# Helper Functions
def get_point_or_404(point_id: str) -> SemanticPoint:
    point = semantic_space.get_point(point_id)
    if point is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Point '{point_id}' not found"
        )
    return point

# API Endpoints
@router.post("/points/", response_model=PointResponse, status_code=status.HTTP_201_CREATED)
async def create_point(point: PointCreate):
    """Create a new point in the semantic space"""
    try:
        point_data = point.dict()
        if point_data.get('name') and semantic_space.get_point(point_data['name']):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Point with name '{point_data['name']}' already exists"
            )
        
        new_point = SemanticPoint(**point_data)
        semantic_space.add_point(new_point)
        return new_point
    except Exception as e:
        logger.error(f"Error creating point: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/points/", response_model=List[PointResponse])
async def list_points(
    skip: int = 0,
    limit: int = 100,
    name_contains: Optional[str] = None,
    min_truth: Optional[float] = None,
    max_truth: Optional[float] = None
):
    """List points with optional filtering"""
    points = semantic_space.points[skip:skip + limit]
    
    # Apply filters
    if name_contains:
        points = [p for p in points if p.name and name_contains.lower() in p.name.lower()]
    if min_truth is not None:
        points = [p for p in points if p.i >= min_truth]
    if max_truth is not None:
        points = [p for p in points if p.i <= max_truth]
    
    return points

@router.get("/points/{point_id}", response_model=PointResponse)
async def get_point(point_id: str):
    """Get a specific point by ID"""
    return get_point_or_404(point_id)

@router.patch("/points/{point_id}", response_model=PointResponse)
async def update_point(point_id: str, update_data: PointUpdate):
    """Partially update a point"""
    point = get_point_or_404(point_id)
    
    try:
        update_dict = update_data.dict(exclude_unset=True)
        point.update(**update_dict)
        return point
    except Exception as e:
        logger.error(f"Error updating point {point_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/points/{point_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_point(point_id: str):
    """Delete a point"""
    point = get_point_or_404(point_id)
    try:
        # Create a new space without the deleted point
        new_points = [p for p in semantic_space.points if p.name != point_id]
        semantic_space.points = new_points
        semantic_space._rebuild_index()
    except Exception as e:
        logger.error(f"Error deleting point {point_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete point"
        )

@router.post("/distance/", response_model=DistanceResponse)
async def calculate_distance(request: DistanceRequest):
    """Calculate distance between two points"""
    start_time = time.perf_counter()
    
    point1 = get_point_or_404(request.point1_id)
    point2 = get_point_or_404(request.point2_id)
    
    try:
        distance = semantic_space.calculate_distance(point1, point2)
        uncertainty = semantic_space.calculate_uncertainty(point1, point2)
        
        return {
            "distance": distance,
            "uncertainty": uncertainty if uncertainty != float('inf') else None,
            "processing_time_ms": (time.perf_counter() - start_time) * 1000
        }
    except Exception as e:
        logger.error(f"Error calculating distance: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/neighbors/", response_model=List[NeighborResponse])
async def find_neighbors(request: NeighborsRequest):
    """Find nearest neighbors to a point"""
    point = get_point_or_404(request.point_id)
    
    try:
        neighbors = semantic_space.find_nearest_neighbors(point, request.k)
        return [
            {
                "point": neighbor[0],
                "distance": neighbor[1],
                "uncertainty": semantic_space.calculate_uncertainty(point, neighbor[0])
            }
            for neighbor in neighbors
        ]
    except Exception as e:
        logger.error(f"Error finding neighbors: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/import/bulk/", response_model=BulkImportResponse)
async def bulk_import_points(
    points: List[PointCreate],
    background_tasks: BackgroundTasks
):
    """Import multiple points at once"""
    start_time = time.perf_counter()
    imported = 0
    skipped = 0
    errors = []
    
    for idx, point_data in enumerate(points):
        try:
            point = SemanticPoint(**point_data.dict())
            if semantic_space.get_point(point.name):
                skipped += 1
                continue
                
            semantic_space.add_point(point)
            imported += 1
        except Exception as e:
            errors.append({
                "index": idx,
                "name": getattr(point_data, 'name', f"unnamed_{idx}"),
                "error": str(e)
            })
    
    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "processing_time_ms": (time.perf_counter() - start_time) * 1000
    }

@router.get("/export/json/")
async def export_space():
    """Export the entire semantic space as JSON"""
    try:
        temp_file = Path("/tmp/semantic_space_export.json")
        semantic_space.save_to_file(temp_file)
        return {"export_path": str(temp_file.absolute())}
    except Exception as e:
        logger.error(f"Export failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export semantic space"
        )

@router.post("/import/json/")
async def import_space(file_path: str):
    """Import semantic space from JSON file"""
    try:
        global semantic_space
        semantic_space = SemanticSpace.load_from_file(file_path)
        return {"message": f"Successfully imported {len(semantic_space)} points"}
    except Exception as e:
        logger.error(f"Import failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to import semantic space: {str(e)}"
        )

@router.get("/metrics/", response_model=SpaceMetricsResponse)
async def get_metrics():
    """Get metrics about the semantic space"""
    metrics = semantic_space.metrics.__dict__.copy()
    metrics.update({
        "total_points": len(semantic_space),
        "size_bytes": sum(
            len(p.name or '') + len(p.description or '') + p.coords.nbytes
            for p in semantic_space.points
        ),
        "last_updated": max((p.updated_at for p in semantic_space.points), default=0)
    })
    return metrics

@router.post("/search/semantic/", response_model=List[NeighborResponse])
async def semantic_search(
    query: str,
    k: int = 5,
    min_similarity: float = 0.0
):
    """
    Perform semantic search in the space
    
    TODO: Implement actual semantic search using embeddings
    This is a placeholder that currently does a simple text search
    """
    # Simple implementation - will be replaced with actual semantic search
    results = []
    query = query.lower()
    
    for point in semantic_space.points:
        if point.name and query in point.name.lower():
            results.append((point, 1.0))
        elif point.description and query in point.description.lower():
            results.append((point, 1.0))
    
    # Sort by relevance (simplified)
    results.sort(key=lambda x: x[1], reverse=True)
    
    return [
        {"point": point, "distance": 1.0 - score, "uncertainty": None}
        for point, score in results[:k] if score >= min_similarity
    ]
