"""
Renderer agnostic camera/viewport state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class CameraState:
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 10.0])
    angle_x: float = 0.0
    angle_y: float = 0.0
    zoom: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0
    min_zoom: float = 0.05
    max_zoom: float = 50.0
    light_pos: List[float] = field(default_factory=lambda: [5.0, 5.0, 5.0, 1.0])

    # TODO: Implement gluPerspective and wire an actual glOrtho path

    orthographic: bool = False

    def reset(self) -> None:
        self.angle_x = 0.0
        self.angle_y = 0.0
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0

    def snapshot(self) -> Dict[str, Any]:
        return {
            "angle_x": self.angle_x, "angle_y": self.angle_y, "zoom": self.zoom,
            "pan_x": self.pan_x, "pan_y": self.pan_y, "orthographic": self.orthographic,
        }

    def restore(self, snapshot: Dict[str, Any]) -> None:
        for key, value in snapshot.items():
            setattr(self, key, value)