"""
Component that attaches mesh geometry and animation behaviour to a scene
node.

Preserves the AnimatedMeshSource/MeshSample interface used by the
previous scene representation while moving ownership into the component
model.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from helios.core.scene import AnimatedMeshSource


@dataclass
class MeshComponent:
    num_vertices: int
    triangle_indices: np.ndarray
    source: AnimatedMeshSource