"""
Renders the ground grid using a cached GridBuffer.

Grid geometry is generated once on first execution and reused across
frames. Creation is deferred until a valid OpenGL context exists.
"""
from __future__ import annotations

from typing import Optional

from helios.renderers.opengl.grid_buffer import GridBuffer
from helios.renderers.opengl.passes.base import PassContext, RenderPass
from helios.renderers.opengl.render_state import RenderState


class GridPass(RenderPass):
    def __init__(self):
        self._grid: Optional[GridBuffer] = None

    def execute(self, ctx: PassContext) -> None:
        if self._grid is None:
            self._grid = GridBuffer()

        ctx.state_manager.apply(RenderState(depth_test=True, cull_face=False, wireframe=False, blend=False, line_width=1.0))

        program = ctx.shaders.get("unlit")
        program.use()
        ctx.stats.shader_switches += 1
        program.set_mat4("u_view", ctx.view_matrix)
        program.set_mat4("u_projection", ctx.projection_matrix)
        program.set_vec3("u_base_color", self._grid.base_color)

        self._grid.draw(stats=ctx.stats)

    def destroy(self) -> None:
        if self._grid is not None:
            self._grid.destroy()