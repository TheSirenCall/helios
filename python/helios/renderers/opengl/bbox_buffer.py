"""
Dynamic GPU buffer for an axis aligned bounding box.

Stores the 12 edges of a bounding box and updates its vertex data when
the bounds change. The buffer is recreated through standard core profile
OpenGL buffer uploads since immediate mode rendering is not available.
"""
from __future__ import annotations

from typing import Optional, Sequence, Tuple

import numpy as np
import OpenGL.GL as gl

# The 12 box edges as pairs of corner indices. Corners follow the shared
# bounding box ordering: min-min-min, max-min-min, max-max-min,
# min-max-min, then the corresponding four corners at max-z.
_EDGE_INDICES = [
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7),
]


class BoundingBoxLineBuffer:
    def __init__(self):
        self.vao = gl.glGenVertexArrays(1)
        self.vbo = gl.glGenBuffers(1)
        self.vertex_count = 0

        gl.glBindVertexArray(self.vao)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)
        gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, gl.GL_FALSE, 0, None)
        gl.glEnableVertexAttribArray(0)
        gl.glBindVertexArray(0)

    def update(self, corners: Sequence[Tuple[float, float, float]]) -> None:
        lines = []
        for a, b in _EDGE_INDICES:
            lines.append(corners[a])
            lines.append(corners[b])
        vertices = np.array(lines, dtype=np.float32)
        self.vertex_count = len(vertices)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, vertices.nbytes, vertices, gl.GL_DYNAMIC_DRAW)

    def draw(self, stats=None) -> None:
        if self.vertex_count == 0:
            return
        gl.glBindVertexArray(self.vao)
        gl.glDrawArrays(gl.GL_LINES, 0, self.vertex_count)
        gl.glBindVertexArray(0)
        if stats is not None:
            stats.draw_calls += 1

    def destroy(self) -> None:
        gl.glDeleteVertexArrays(1, [self.vao])
        gl.glDeleteBuffers(1, [self.vbo])