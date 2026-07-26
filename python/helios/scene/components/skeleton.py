"""
Component marking nodes that participate in skeletal animation.

Stores minimal skeleton-related metadata used by queries and statistics,
while keeping skinning evaluation inside the mesh animation source. This
allows systems to identify skinned nodes without depending on the
internal skinning implementation.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SkeletonComponent:
    skeleton_path: str = ""