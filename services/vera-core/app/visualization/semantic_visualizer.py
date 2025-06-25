import os
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from typing import List, Dict, Any, Optional, Union, Tuple
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import networkx as nx
from sklearn.manifold import TSNE
from umap import UMAP

from ..models.semantic_space import SemanticSpace, SemanticPoint
from ..core.logging import get_logger

logger = get_logger(__name__)


class SemanticVisualizer:
    """Класс для визуализации семантического пространства"""
    
    def __init__(self, semantic_space: SemanticSpace):
        self.space = semantic_space
        self.figures_dir = Path("figures")
        self.figures_dir.mkdir(exist_ok=True)
    
    def plot_2d_scatter(
        self, 
        method: str = 'pca', 
        color_by: str = None,
        size: int = 10,
        title: str = "2D визуализация семантического пространства",
        save_path: str = None,
        show: bool = True,
        **kwargs
    ) -> go.Figure:
        """
        Создаёт 2D scatter plot семантического пространства.
        
        Args:
            method: Метод понижения размерности ('pca', 'tsne', 'umap')
            color_by: По какому признаку раскрашивать точки (None, 'cluster', 'category' и т.д.)
            size: Размер точек
            title: Заголовок графика
            save_path: Путь для сохранения (если None, не сохраняется)
            show: Показывать ли график
            **kwargs: Дополнительные параметры для plotly.express.scatter
            
        Returns:
            go.Figure: Объект графика Plotly
        """
        if len(self.space.points) < 2:
            logger.warning("Недостаточно точек для визуализации")
            return None
            
        # Получаем векторы и имена точек
        vectors = np.array([p.to_vector() for p in self.space.points])
        names = [p.name or str(i) for i, p in enumerate(self.space.points)]
        
        # Понижаем размерность до 2D
        if method == 'pca':
            from sklearn.decomposition import PCA
            coords = PCA(n_components=2).fit_transform(vectors)
            x, y = coords[:, 0], coords[:, 1]
            
        elif method == 'tsne':
            coords = TSNE(n_components=2, random_state=42).fit_transform(vectors)
            x, y = coords[:, 0], coords[:, 1]
            
        elif method == 'umap':
            coords = UMAP(n_components=2, random_state=42).fit_transform(vectors)
            x, y = coords[:, 0], coords[:, 1]
            
        else:
            raise ValueError(f"Неподдерживаемый метод понижения размерности: {method}")
        
        # Создаем DataFrame для Plotly
        import pandas as pd
        df = pd.DataFrame({
            'x': x,
            'y': y,
            'name': names,
            'text': [f"{n}<br>{p.description or ''}" for n, p in zip(names, self.space.points)]
        })
        
        # Добавляем информацию для раскраски, если указана
        if color_by == 'cluster':
            from sklearn.cluster import KMeans
            n_clusters = min(10, len(self.space.points) // 2)
            if n_clusters > 1:
                kmeans = KMeans(n_clusters=n_clusters, random_state=42).fit(vectors)
                df['cluster'] = kmeans.labels_.astype(str)
        
        # Создаем график
        fig = px.scatter(
            df, 
            x='x', 
            y='y',
            color=color_by if color_by in df.columns else None,
            size=[size] * len(df),
            hover_name='name',
            hover_data={'x': ':.3f', 'y': ':.3f'},
            title=title,
            **kwargs
        )
        
        # Настраиваем отображение
        fig.update_traces(
            marker=dict(
                size=size,
                line=dict(width=1, color='DarkSlateGrey')
            ),
            selector=dict(mode='markers')
        )
        
        fig.update_layout(
            xaxis_title=f"{method.upper()} 1",
            yaxis_title=f"{method.upper()} 2",
            hoverlabel=dict(
                bgcolor="white",
                font_size=12,
                font_family="Arial"
            ),
            showlegend=color_by in df.columns
        )
        
        # Сохраняем при необходимости
        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            fig.write_html(str(save_path))
            
        if show:
            fig.show()
            
        return fig
    
    def plot_3d_scatter(
        self, 
        method: str = 'pca',
        color_by: str = None,
        size: int = 5,
        title: str = "3D визуализация семантического пространства",
        save_path: str = None,
        show: bool = True,
        **kwargs
    ) -> go.Figure:
        """
        Создаёт 3D scatter plot семантического пространства.
        
        Args:
            method: Метод понижения размерности ('pca', 'tsne', 'umap')
            color_by: По какому признаку раскрашивать точки
            size: Размер точек
            title: Заголовок графика
            save_path: Путь для сохранения (если None, не сохраняется)
            show: Показывать ли график
            **kwargs: Дополнительные параметры для plotly.express.scatter_3d
            
        Returns:
            go.Figure: Объект 3D графика Plotly
        """
        if len(self.space.points) < 3:
            logger.warning("Недостаточно точек для 3D визуализации")
            return None
            
        # Получаем векторы и имена точек
        vectors = np.array([p.to_vector() for p in self.space.points])
        names = [p.name or str(i) for i, p in enumerate(self.space.points)]
        
        # Понижаем размерность до 3D
        if method == 'pca':
            from sklearn.decomposition import PCA
            coords = PCA(n_components=3).fit_transform(vectors)
            x, y, z = coords[:, 0], coords[:, 1], coords[:, 2]
            
        elif method == 'tsne':
            coords = TSNE(n_components=3, random_state=42).fit_transform(vectors)
            x, y, z = coords[:, 0], coords[:, 1], coords[:, 2]
            
        elif method == 'umap':
            coords = UMAP(n_components=3, random_state=42).fit_transform(vectors)
            x, y, z = coords[:, 0], coords[:, 1], coords[:, 2]
            
        else:
            raise ValueError(f"Неподдерживаемый метод понижения размерности: {method}")
        
        # Создаем DataFrame для Plotly
        import pandas as pd
        df = pd.DataFrame({
            'x': x,
            'y': y,
            'z': z,
            'name': names,
            'text': [f"{n}<br>{p.description or ''}" for n, p in zip(names, self.space.points)]
        })
        
        # Добавляем информацию для раскраски, если указана
        if color_by == 'cluster':
            from sklearn.cluster import KMeans
            n_clusters = min(10, len(self.space.points) // 2)
            if n_clusters > 1:
                kmeans = KMeans(n_clusters=n_clusters, random_state=42).fit(vectors)
                df['cluster'] = kmeans.labels_.astype(str)
        
        # Создаем 3D график
        fig = px.scatter_3d(
            df, 
            x='x', 
            y='y',
            z='z',
            color=color_by if color_by in df.columns else None,
            size=[size] * len(df),
            hover_name='name',
            hover_data={'x': ':.3f', 'y': ':.3f', 'z': ':.3f'},
            title=title,
            **kwargs
        )
        
        # Настраиваем отображение
        fig.update_traces(
            marker=dict(
                size=size,
                line=dict(width=1, color='DarkSlateGrey')
            ),
            selector=dict(mode='markers')
        )
        
        fig.update_layout(
            scene=dict(
                xaxis_title=f"{method.upper()} 1",
                yaxis_title=f"{method.upper()} 2",
                zaxis_title=f"{method.upper()} 3"
            ),
            hoverlabel=dict(
                bgcolor="white",
                font_size=12,
                font_family="Arial"
            ),
            showlegend=color_by in df.columns
        )
        
        # Сохраняем при необходимости
        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            fig.write_html(str(save_path))
            
        if show:
            fig.show()
            
        return fig
    
    def plot_semantic_network(
        self,
        max_edges: int = 100,
        threshold: float = 0.7,
        title: str = "Семантическая сеть",
        save_path: str = None,
        show: bool = True,
        **kwargs
    ) -> go.Figure:
        """
        Визуализирует семантическое пространство в виде графа связей.
        
        Args:
            max_edges: Максимальное количество рёбер для отображения
            threshold: Порог сходства для отображения связи
            title: Заголовок графика
            save_path: Путь для сохранения (если None, не сохраняется)
            show: Показывать ли график
            **kwargs: Дополнительные параметры для визуализации
            
        Returns:
            go.Figure: Объект графа Plotly
        """
        if len(self.space.points) < 2:
            logger.warning("Недостаточно точек для построения сети")
            return None
            
        # Создаем граф
        G = nx.Graph()
        
        # Добавляем узлы
        for i, point in enumerate(self.space.points):
            G.add_node(
                point.name or str(i),
                description=point.description or ""
            )
        
        # Вычисляем попарные сходства и добавляем рёбра
        similarities = []
        nodes = list(G.nodes())
        
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                sim = self.space.calculate_similarity(
                    self.space.points[i], 
                    self.space.points[j]
                )
                if sim >= threshold:
                    similarities.append((i, j, sim))
        
        # Сортируем по убыванию сходства и берем топ-N
        similarities.sort(key=lambda x: x[2], reverse=True)
        for i, j, sim in similarities[:max_edges]:
            G.add_edge(nodes[i], nodes[j], weight=sim)
        
        # Позиционирование узлов
        pos = nx.spring_layout(G, weight='weight')
        
        # Создаем ребра
        edge_x = []
        edge_y = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
        
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines')
        
        # Создаем узлы
        node_x = []
        node_y = []
        node_text = []
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(f"{node}<br>{G.nodes[node].get('description', '')}")
        
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            hoverinfo='text',
            hovertext=node_text,
            marker=dict(
                showscale=True,
                colorscale='YlGnBu',
                size=10,
                color=[],
                line_width=2))
        
        # Создаем фигуру
        fig = go.Figure(data=[edge_trace, node_trace],
                     layout=go.Layout(
                        title=title,
                        titlefont_size=16,
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20,l=5,r=5,t=40),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                        )
        
        # Сохраняем при необходимости
        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            fig.write_html(str(save_path))
            
        if show:
            fig.show()
            
        return fig
    
    def export_to_html(
        self, 
        output_dir: str = None, 
        prefix: str = "semantic_viz",
        include_2d: bool = True,
        include_3d: bool = True,
        include_network: bool = True,
        **kwargs
    ) -> Dict[str, str]:
        """
        Экспортирует все визуализации в HTML файлы.
        
        Args:
            output_dir: Директория для сохранения (по умолчанию: figures/)
            prefix: Префикс для имён файлов
            include_2d: Включать ли 2D визуализацию
            include_3d: Включать ли 3D визуализацию
            include_network: Включать ли сетевую визуализацию
            **kwargs: Дополнительные параметры для визуализаций
            
        Returns:
            Dict[str, str]: Словарь с путями к сохранённым файлам
        """
        output_dir = Path(output_dir) if output_dir else self.figures_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        result = {}
        
        # Генерируем 2D визуализацию
        if include_2d and len(self.space.points) >= 2:
            path_2d = output_dir / f"{prefix}_2d.html"
            self.plot_2d_scatter(
                save_path=path_2d, 
                show=False,
                **kwargs
            )
            result['2d_plot'] = str(path_2d.absolute())
        
        # Генерируем 3D визуализацию
        if include_3d and len(self.space.points) >= 3:
            path_3d = output_dir / f"{prefix}_3d.html"
            self.plot_3d_scatter(
                save_path=path_3d,
                show=False,
                **kwargs
            )
            result['3d_plot'] = str(path_3d.absolute())
        
        # Генерируем сетевую визуализацию
        if include_network and len(self.space.points) >= 2:
            path_net = output_dir / f"{prefix}_network.html"
            self.plot_semantic_network(
                save_path=path_net,
                show=False,
                **kwargs
            )
            result['network_plot'] = str(path_net.absolute())
        
        return result
