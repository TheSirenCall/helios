"""
Render ready scene data produced by SceneExtractor for a specific frame.

This is the only scene representation consumed by the renderer. It has
no knowledge of the SceneGraph, Components, or pxr.

The scene is represented as a collection of meshes to support future
extensions such as per mesh materials and visibility. Currently,
SceneExtractor produces a single mesh, matching the behavior of
SceneGraph.sample().

node_ranges maps scene paths to vertex ranges within the mesh for
picking and highlighting.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np


@dataclass(frozen=True)
class NodeRange:
    """
    Maps a SceneNode to its vertex and index ranges within the combined
    scene RenderableMesh.

    The vertex range supports geometry queries such as picking and bounding
    box computation. The index range allows SelectionPass to render the
    node's triangles directly from the existing index buffer instead of
    creating a separate mesh or uploading additional data.
    """
    path: str
    vertex_start: int
    vertex_count: int
    index_start: int
    index_count: int


@dataclass
class RenderableMesh:
    name: str
    vertices: np.ndarray  # (N, 3) float32
    normals: np.ndarray   # (N, 3) float32
    indices: np.ndarray   # uint32
    colors: np.ndarray = field(default_factory=lambda: np.zeros((0, 3), dtype=np.float32))


@dataclass
class RenderScene:
    frame: float
    meshes: List[RenderableMesh]
    bounding_box: Optional[Sequence[Tuple[float, float, float]]] = None
    node_ranges: List[NodeRange] = field(default_factory=list)