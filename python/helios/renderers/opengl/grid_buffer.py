"""
Static ground grid geometry for modern OpenGL rendering.

The grid is built once and stored in a GPU buffer, replacing
per frame immediate mode generation with persistent geometry that can be
drawn efficiently across frames.
"""
from __future__ import annotations

import numpy as np
import OpenGL.GL as gl


class GridBuffer:
    def __init__(self, half_extent: int = 10, base_color=(0.5, 0.5, 0.5)):
        self.base_color = base_color

        lines = []
        for i in range(-half_extent, half_extent + 1):
            lines.append([i, 0, -half_extent])
            lines.append([i, 0, half_extent])
            lines.append([-half_extent, 0, i])
            lines.append([half_extent, 0, i])
        vertices = np.array(lines, dtype=np.float32)
        self.vertex_count = len(vertices)

        self.vao = gl.glGenVertexArrays(1)
        self.vbo = gl.glGenBuffers(1)
        gl.glBindVertexArray(self.vao)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, vertices.nbytes, vertices, gl.GL_STATIC_DRAW)
        gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, gl.GL_FALSE, 0, None)
        gl.glEnableVertexAttribArray(0)
        gl.glBindVertexArray(0)

    def draw(self, stats=None) -> None:
        gl.glBindVertexArray(self.vao)
        gl.glDrawArrays(gl.GL_LINES, 0, self.vertex_count)
        gl.glBindVertexArray(0)
        if stats is not None:
            stats.draw_calls += 1

    def destroy(self) -> None:
        gl.glDeleteVertexArrays(1, [self.vao])
        gl.glDeleteBuffers(1, [self.vbo])