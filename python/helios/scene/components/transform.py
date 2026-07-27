"""
Stores the node transform resolver used to evaluate world matrices over
time.

The resolver is provided by the importer and follows a common interface,
allowing different formats to provide their own transform evaluation
logic while keeping the scene graph independent of file specific APIs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

WorldMatrixResolver = Callable[[float], np.ndarray]


@dataclass
class TransformComponent:
    resolve_world_matrix: WorldMatrixResolver