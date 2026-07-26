"""
Material abstraction
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class Texture:
    """Placeholder for future image texture support (UsdPreviewSurface/ MaterialX)."""
    path: str


@dataclass
class Material:
    base_color: Tuple[float, float, float] = (0.7, 0.7, 0.7)
    opacity: float = 1.0
    diffuse_texture: Optional[Texture] = None