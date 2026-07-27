
from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Optional, Tuple


class SelectionMode(enum.Enum):
    OBJECT = "object"
    FACE = "face"
    EDGE = "edge"
    VERTEX = "vertex"


@dataclass(frozen=True)
class PickingResult:
    """
    Always returned by Renderer.pick(), even on a miss (path=None),
    rather than a bare Optional[str].
    """

    path: Optional[str] = None
    hit_point: Optional[Tuple[float, float, float]] = None
    face_index: Optional[int] = None

    def __bool__(self) -> bool:
        return self.path is not None