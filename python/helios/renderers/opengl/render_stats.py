"""
Per frame rendering statistics collected during GPU execution.

Counters are reset at the beginning of each frame and updated by render
passes and GPU resource managers as work is performed. This class only
stores render metrics and has no dependency on UI or event systems.
"""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class RenderStats:
    cpu_frame_ms: float = 0.0
    draw_calls: int = 0
    triangles: int = 0
    vertices: int = 0
    buffer_uploads: int = 0
    uploaded_vertices: int = 0
    shader_switches: int = 0

    def reset(self) -> None:
        self.cpu_frame_ms = 0.0
        self.draw_calls = 0
        self.triangles = 0
        self.vertices = 0
        self.buffer_uploads = 0
        self.uploaded_vertices = 0
        self.shader_switches = 0


class FrameTimer:
    """
    Context manager for measuring CPU frame time.

    When used with FrameTimer(stats), records the elapsed wall clock time
    of the wrapped block and stores the result in stats.cpu_frame_ms.
    """

    def __init__(self, stats: RenderStats):
        self.stats = stats
        self._start = 0.0

    def __enter__(self) -> "FrameTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc) -> None:
        self.stats.cpu_frame_ms = (time.perf_counter() - self._start) * 1000.0