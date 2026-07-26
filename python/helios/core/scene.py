"""
Defines the animation interface shared by all importer backends.

SceneGraph, SceneNode, and MeshComponent own the scene representation.
AnimatedMeshSource and MeshSample remain here because they provide the
common interface used by importers and MeshComponent, regardless of file
format or scene hierarchy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass
class MeshSample:
    """A single mesh's world space geometry at one point in time."""
    vertices: np.ndarray  # (N, 3) float64, world space, un-normalized
    normals: np.ndarray   # (N, 3) float64, world space, unit length


class AnimatedMeshSource(Protocol):
    """
    Defines the interface for resolving animated mesh data.

    Concrete implementations are provided by importer backends. By depending
    only on this Protocol, the renderer and other systems remain agnostic to
    how animation is evaluated or which file format produced the data.
    """

    def sample(self, frame: float) -> MeshSample: ...