"""
Renders selection and hover highlighting.

The pass draws selected node index ranges from GeometryPass's existing
element buffers, avoiding duplicate geometry uploads. The current
outline is implemented as a wireframe silhouette; screen space edge
outlining would require a separate post-processing pipeline.
"""
from __future__ import annotations

import ctypes
from typing import List, Optional, Sequence

import OpenGL.GL as gl

from helios.renderers.opengl.bbox_buffer import BoundingBoxLineBuffer
from helios.renderers.opengl.passes.base import PassContext, RenderPass
from helios.renderers.opengl.passes.geometry_pass import GeometryPass
from helios.renderers.opengl.render_state import RenderState

_SELECTED_COLOR = (1.0, 0.8, 0.0)  # yellow
_HOVER_COLOR = (0.4, 0.85, 1.0) # cyan


class SelectionPass(RenderPass):
    def __init__(self, geometry_pass: GeometryPass):
        self._geometry_pass = geometry_pass
        self._selected_paths: List[str] = []
        self._hover_path: Optional[str] = None
        self._bbox_buffer: Optional[BoundingBoxLineBuffer] = None

    def set_selected(self, node_paths: Sequence[str]) -> None:
        self._selected_paths = list(node_paths)

    def set_hover(self, node_path: Optional[str]) -> None:
        self._hover_path = node_path

    def execute(self, ctx: PassContext) -> None:
        if not self._selected_paths and self._hover_path is None:
            return

        buffer = self._geometry_pass.get_mesh_buffer("scene")
        if buffer is None:
            return
        if self._bbox_buffer is None:
            self._bbox_buffer = BoundingBoxLineBuffer()

        program = ctx.shaders.get("unlit")
        program.use()
        ctx.stats.shader_switches += 1
        program.set_mat4("u_view", ctx.view_matrix)
        program.set_mat4("u_projection", ctx.projection_matrix)

        # Hover drawn first, selection drawn after
        if self._hover_path is not None and self._hover_path not in self._selected_paths:
            self._draw_outline(ctx, buffer, self._hover_path, _HOVER_COLOR)
        for path in self._selected_paths:
            self._draw_outline(ctx, buffer, path, _SELECTED_COLOR)

    def _draw_outline(self, ctx: PassContext, buffer, path: str, color) -> None:
        node_range = next((nr for nr in ctx.render_scene.node_ranges if nr.path == path), None)
        if node_range is None or node_range.index_count == 0:
            return

        ctx.shaders.get("unlit").set_vec3("u_base_color", color)

        # Wireframe silhouette
        ctx.state_manager.apply(RenderState(depth_test=True, cull_face=False, wireframe=True, blend=False, line_width=2.0))
        gl.glBindVertexArray(buffer.vao)
        gl.glDrawElements(
            gl.GL_TRIANGLES, node_range.index_count, gl.GL_UNSIGNED_INT,
            ctypes.c_void_p(node_range.index_start * 4),
        )
        gl.glBindVertexArray(0)
        ctx.stats.draw_calls += 1

        # Bounding box overlay
        vertices = ctx.render_scene.meshes[0].vertices
        node_vertices = vertices[node_range.vertex_start:node_range.vertex_start + node_range.vertex_count]
        if node_vertices.size == 0:
            return
        box_min = node_vertices.min(axis=0)
        box_max = node_vertices.max(axis=0)
        corners = [
            (box_min[0], box_min[1], box_min[2]), (box_max[0], box_min[1], box_min[2]),
            (box_max[0], box_max[1], box_min[2]), (box_min[0], box_max[1], box_min[2]),
            (box_min[0], box_min[1], box_max[2]), (box_max[0], box_min[1], box_max[2]),
            (box_max[0], box_max[1], box_max[2]), (box_min[0], box_max[1], box_max[2]),
        ]
        ctx.state_manager.apply(RenderState(depth_test=True, cull_face=False, wireframe=False, blend=False, line_width=1.0))
        self._bbox_buffer.update(corners)
        self._bbox_buffer.draw(stats=ctx.stats)

    def destroy(self) -> None:
        if self._bbox_buffer is not None:
            self._bbox_buffer.destroy()