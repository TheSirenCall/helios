"""
Component that attaches material data to a scene node.

Stores a Material and optional resolved vertex color data separately from
geometry, keeping rendering/material concerns independent from mesh
storage. Future material systems such as UsdShade or MaterialX can extend
this component without changing geometry components.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from helios.core.material import Material


@dataclass
class MaterialComponent:
    material: Material
    # Optional vertex color buffer (N, 3) float32 values aligned with the
    # mesh's point order. Set only for true per vertex color data; when None,
    # SceneGraph.sample() uses material.base_color as a uniform color for the
    # mesh.
    vertex_colors: Optional[np.ndarray] = None