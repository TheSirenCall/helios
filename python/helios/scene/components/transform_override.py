"""
Stores a user authored transform delta applied after the node's resolved
world transform.

Keeps editing separate from importer provided transform evaluation, so
Move/Rotate/Scale operations modify application state rather than
format specific animation or transform data. Changes remain undoable
through the Command framework.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class TransformOverrideComponent:
    matrix: np.ndarray = field(default_factory=lambda: np.eye(4, dtype=np.float64))