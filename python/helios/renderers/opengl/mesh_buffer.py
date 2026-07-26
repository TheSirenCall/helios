"""
Owns the GPU resources for a single mesh.

Manages the mesh VAO, VBOs, and EBO used for rendering. Updates only
reupload data when new array objects are provided, relying on
SceneExtractor's stable array reuse for unchanged scene frames.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import OpenGL.GL as gl


class MeshBuffer:
    def __init__(self):
        self.vao = gl.glGenVertexArrays(1)
        self.vbo_vertices = gl.glGenBuffers(1)
        self.vbo_normals = gl.glGenBuffers(1)
        self.vbo_colors = gl.glGenBuffers(1)
        self.ebo = gl.glGenBuffers(1)
        self.vertex_count = 0
        self.index_count = 0

        self._last_vertices: Optional[np.ndarray] = None
        self._last_normals: Optional[np.ndarray] = None
        self._last_colors: Optional[np.ndarray] = None
        self._last_indices: Optional[np.ndarray] = None

        self._setup_attributes()

    def _setup_attributes(self) -> None:
        gl.glBindVertexArray(self.vao)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo_vertices)
        gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, gl.GL_FALSE, 0, None)
        gl.glEnableVertexAttribArray(0)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo_normals)
        gl.glVertexAttribPointer(1, 3, gl.GL_FLOAT, gl.GL_FALSE, 0, None)
        gl.glEnableVertexAttribArray(1)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo_colors)
        gl.glVertexAttribPointer(2, 3, gl.GL_FLOAT, gl.GL_FALSE, 0, None)
        gl.glEnableVertexAttribArray(2)

        # Element buffer binding is part of VAO state, so binding it here
        # while vao is bound should be  enough
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.ebo)

        gl.glBindVertexArray(0)

    def update(self, vertices: np.ndarray, normals: np.ndarray, indices: np.ndarray,
               colors: Optional[np.ndarray] = None, stats=None) -> bool:
        """
        Updates GPU mesh data when required.

        Returns True if a buffer upload occurred, otherwise False when the
        existing buffers were unchanged. Vertex colors are optional for
        compatibility with callers that do not provide color data and default
        to white when omitted.
        """
        if colors is None:
            colors = np.ones_like(vertices, dtype=np.float32)

        if (vertices is self._last_vertices
                and normals is self._last_normals
                and colors is self._last_colors
                and indices is self._last_indices):
            return False

        topology_changed = indices is not self._last_indices or len(indices) != self.index_count

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo_vertices)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, vertices.nbytes, vertices, gl.GL_DYNAMIC_DRAW)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo_normals)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, normals.nbytes, normals, gl.GL_DYNAMIC_DRAW)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo_colors)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, colors.nbytes, colors, gl.GL_DYNAMIC_DRAW)

        if topology_changed:
            gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.ebo)
            gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, gl.GL_STATIC_DRAW)
            self.index_count = len(indices)

        self.vertex_count = len(vertices)
        self._last_vertices = vertices
        self._last_normals = normals
        self._last_colors = colors
        self._last_indices = indices

        if stats is not None:
            stats.buffer_uploads += 1
            stats.uploaded_vertices += self.vertex_count

        return True

    def draw(self, stats=None) -> None:
        if self.index_count == 0:
            return
        gl.glBindVertexArray(self.vao)
        gl.glDrawElements(gl.GL_TRIANGLES, self.index_count, gl.GL_UNSIGNED_INT, None)
        gl.glBindVertexArray(0)
        if stats is not None:
            stats.draw_calls += 1
            stats.triangles += self.index_count // 3
            stats.vertices += self.vertex_count

    def destroy(self) -> None:
        gl.glDeleteVertexArrays(1, [self.vao])
        gl.glDeleteBuffers(1, [self.vbo_vertices])
        gl.glDeleteBuffers(1, [self.vbo_normals])
        gl.glDeleteBuffers(1, [self.vbo_colors])
        gl.glDeleteBuffers(1, [self.ebo])