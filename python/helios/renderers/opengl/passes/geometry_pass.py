"""
Renders opaque scene geometry.

Owns the MeshBuffer cache for renderable meshes, reusing GPU resources
across frames and updating buffers only when the underlying mesh data
changes.
"""
from __future__ import annotations

from typing import Dict, Optional

from helios.renderers.opengl.mesh_buffer import MeshBuffer
from helios.renderers.opengl.passes.base import PassContext, RenderPass
from helios.renderers.opengl.render_state import RenderState


class GeometryPass(RenderPass):
    def __init__(self):
        self._buffers: Dict[str, MeshBuffer] = {}

    def execute(self, ctx: PassContext) -> None:
        ctx.state_manager.apply(RenderState(depth_test=True, cull_face=False, wireframe=False, blend=False, line_width=1.0))

        program = ctx.shaders.get("lit")
        program.use()
        ctx.stats.shader_switches += 1
        program.set_mat4("u_view", ctx.view_matrix)
        program.set_mat4("u_projection", ctx.projection_matrix)
        program.set_vec3("u_light_pos", ctx.camera.light_pos[:3])

        for mesh in ctx.render_scene.meshes:
            if mesh.indices.size == 0:
                continue
            buffer = self._buffers.setdefault(mesh.name, MeshBuffer())
            buffer.update(mesh.vertices, mesh.normals, mesh.indices, colors=mesh.colors, stats=ctx.stats)
            buffer.draw(stats=ctx.stats)

    def get_mesh_buffer(self, name: str) -> Optional[MeshBuffer]:
        """
        Provides indexed geometry ranges for SelectionPass.

        Returns index ranges that can be rendered from the existing element
        buffer using an offset, allowing selection rendering without additional
        GPU uploads or duplicated buffers.
        """
        return self._buffers.get(name)

    def destroy(self) -> None:
        for buffer in self._buffers.values():
            buffer.destroy()
        self._buffers.clear()