import numpy as np
import plotly.graph_objects as go
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
import json

from app.models.semantic_space import SemanticSpace, SemanticPoint

class SemanticSpaceVisualizer:
    """Visualization tools for semantic space"""
    
    def __init__(self, semantic_space: SemanticSpace):
        self.space = semantic_space
        self.dimension_names = ['X', 'Y', 'Z', 'T', 'O', 'I', 'N']
        
    def project_to_2d(self, points: np.ndarray, method: str = 'pca', **kwargs) -> np.ndarray:
        """
        Project high-dimensional points to 2D
        
        Args:
            points: (n_points, 7) array of points in semantic space
            method: 'pca', 'tsne', or 'umap'
            **kwargs: Additional arguments for the projection method
            
        Returns:
            (n_points, 2) array of 2D coordinates
        """
        if method == 'pca':
            from sklearn.decomposition import PCA
            reducer = PCA(n_components=2, **kwargs)
        elif method == 'tsne':
            from sklearn.manifold import TSNE
            reducer = TSNE(n_components=2, **kwargs)
        elif method == 'umap':
            from umap import UMAP
            reducer = UMAP(n_components=2, **kwargs)
        else:
            raise ValueError(f"Unsupported projection method: {method}")
            
        return reducer.fit_transform(points)
    
    def create_2d_scatter(self, dim1: int = 0, dim2: int = 1, 
                         color_by: str = 'i', size_by: str = 'n',
                         hover_data: List[str] = None, 
                         title: str = None) -> go.Figure:
        """
        Create a 2D scatter plot of the semantic space
        
        Args:
            dim1: Index of first dimension to plot (0-6)
            dim2: Index of second dimension to plot (0-6)
            color_by: Which dimension to use for color ('x', 'y', 'z', 't', 'o', 'i', 'n' or 'name')
            size_by: Which dimension to use for point size ('x', 'y', 'z', 't', 'o', 'i', 'n')
            hover_data: List of additional data to show on hover
            title: Plot title
            
        Returns:
            plotly Figure object
        """
        if not self.space.points:
            raise ValueError("No points in the semantic space")
            
        points = np.array([p.to_vector() for p in self.space.points])
        
        # Prepare hover text
        hover_texts = []
        for point in self.space.points:
            text = []
            if point.name:
                text.append(f"<b>{point.name}</b>")
            if point.description:
                text.append(f"{point.description[:100]}..." if len(point.description) > 100 else point.description)
            
            # Add requested dimensions
            for dim in hover_data or []:
                if hasattr(point, dim):
                    text.append(f"{dim.upper()}: {getattr(point, dim):.3f}")
            
            hover_texts.append("<br>".join(text))
        
        # Get color and size values
        color_values = self._get_dimension_values(color_by)
        size_values = self._get_dimension_values(size_by)
        
        # Normalize sizes for better visualization
        if size_values is not None:
            size_values = 10 + 15 * (size_values - np.min(size_values)) / (np.max(size_values) - np.min(size_values) + 1e-8)
        else:
            size_values = 10
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=points[:, dim1],
            y=points[:, dim2],
            mode='markers+text',
            marker=dict(
                size=size_values,
                color=color_values,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title=self.dimension_names[dim1] if color_by in 'xyztion' else color_by.title())
            ),
            text=[p.name or f"Point {i}" for i, p in enumerate(self.space.points)],
            textposition='top center',
            hoverinfo='text',
            hovertext=hover_texts,
            name='Semantic Points'
        ))
        
        # Add dimension labels
        fig.update_layout(
            title=title or f"Semantic Space: {self.dimension_names[dim1]} vs {self.dimension_names[dim2]}",
            xaxis_title=self.dimension_names[dim1],
            yaxis_title=self.dimension_names[dim2],
            hovermode='closest',
            showlegend=False
        )
        
        return fig
    
    def create_3d_scatter(self, dims: Tuple[int, int, int] = (0, 1, 2),
                          color_by: str = 'i', size_by: str = 'n',
                          hover_data: List[str] = None) -> go.Figure:
        """
        Create a 3D scatter plot of the semantic space
        
        Args:
            dims: Tuple of three dimension indices to use for x, y, z axes
            color_by: Which dimension to use for color
            size_by: Which dimension to use for point size
            hover_data: List of additional data to show on hover
            
        Returns:
            plotly Figure object
        """
        if not self.space.points:
            raise ValueError("No points in the semantic space")
            
        points = np.array([p.to_vector() for p in self.space.points])
        
        # Prepare hover text
        hover_texts = []
        for point in self.space.points:
            text = []
            if point.name:
                text.append(f"<b>{point.name}</b>")
            if point.description:
                text.append(f"{point.description[:100]}..." if len(point.description) > 100 else point.description)
            
            # Add requested dimensions
            for dim in hover_data or []:
                if hasattr(point, dim):
                    text.append(f"{dim.upper()}: {getattr(point, dim):.3f}")
            
            hover_texts.append("<br>".join(text))
        
        # Get color and size values
        color_values = self._get_dimension_values(color_by)
        size_values = self._get_dimension_values(size_by)
        
        # Normalize sizes for better visualization
        if size_values is not None:
            size_values = 5 + 15 * (size_values - np.min(size_values)) / (np.max(size_values) - np.min(size_values) + 1e-8)
        else:
            size_values = 10
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter3d(
            x=points[:, dims[0]],
            y=points[:, dims[1]],
            z=points[:, dims[2]],
            mode='markers+text',
            marker=dict(
                size=size_values,
                color=color_values,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title=self.dimension_names[dims[0]] if color_by in 'xyztion' else color_by.title())
            ),
            text=[p.name or f"Point {i}" for i, p in enumerate(self.space.points)],
            textposition='top center',
            hoverinfo='text',
            hovertext=hover_texts,
            name='Semantic Points'
        ))
        
        # Add dimension labels
        fig.update_layout(
            scene=dict(
                xaxis_title=self.dimension_names[dims[0]],
                yaxis_title=self.dimension_names[dims[1]],
                zaxis_title=self.dimension_names[dims[2]]
            ),
            title=f"3D Semantic Space: {self.dimension_names[dims[0]]}-{self.dimension_names[dims[1]]}-{self.dimension_names[dims[2]]}",
            hovermode='closest',
            showlegend=False
        )
        
        return fig
    
    def _get_dimension_values(self, dim: str) -> np.ndarray:
        """Get values for a given dimension"""
        if dim == 'x':
            return np.array([p.x for p in self.space.points])
        elif dim == 'y':
            return np.array([p.y for p in self.space.points])
        elif dim == 'z':
            return np.array([p.z for p in self.space.points])
        elif dim == 't':
            return np.array([p.t for p in self.space.points])
        elif dim == 'o':
            return np.array([p.o.value for p in self.space.points])
        elif dim == 'i':
            return np.array([p.i for p in self.space.points])
        elif dim == 'n':
            return np.array([p.n for p in self.space.points])
        elif dim == 'name':
            return np.array([hash(p.name or str(i)) for i, p in enumerate(self.space.points)])
        return None
    
    def save_plot(self, fig: go.Figure, filename: str, format: str = 'html', **kwargs):
        """Save plot to file"""
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'html':
            fig.write_html(str(output_path), **kwargs)
        elif format == 'png':
            fig.write_image(str(output_path), **kwargs)
        elif format == 'json':
            fig.write_json(str(output_path), **kwargs)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        return str(output_path.absolute())
