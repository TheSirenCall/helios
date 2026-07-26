"""
OpenGL implementation of the Renderer interface.

Handles render orchestration, including pass execution, shader and state
management. GPU resource ownership remains isolated in dedicated classes
such as ShaderManager, MeshBuffer, and GridBuffer.

Lighting uses world space positions, matching the current shader-based
pipeline and CameraState representation.
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np
import OpenGL.GL as gl

from helios.core.camera import CameraState
from helios.core.picking import PickingResult, SelectionMode
from helios.core.render_scene import RenderScene
from helios.renderers.base import Renderer
from helios.renderers.opengl.passes.base import PassContext
from helios.renderers.opengl.passes.geometry_pass import GeometryPass
from helios.renderers.opengl.passes.grid_pass import GridPass
from helios.renderers.opengl.passes.selection_pass import SelectionPass
from helios.renderers.opengl.render_state import RenderStateManager
from helios.renderers.opengl.render_stats import FrameTimer, RenderStats
from helios.renderers.opengl.shader_manager import ShaderManager


class OpenGLRenderer(Renderer):
    def __init__(self):
        self.shaders = ShaderManager()
        self.state_manager = RenderStateManager()
        self.stats = RenderStats()
        # Pass order defines the render, grid establishes the
        # background depth, geometry draws the scene, and selection renders on
        # top. Additional passes can be appended without modifying existing ones.
        self._geometry_pass = GeometryPass()
        self._selection_pass = SelectionPass(self._geometry_pass)
        self._passes = [GridPass(), self._geometry_pass, self._selection_pass]
        self._width = 1
        self._height = 1

    def initialize(self) -> None:
        if bool(gl.glGetString(gl.GL_VERSION)) and hasattr(gl, "GL_DEBUG_OUTPUT"):
            try:
                gl.glEnable(gl.GL_DEBUG_OUTPUT)
                gl.glEnable(gl.GL_DEBUG_OUTPUT_SYNCHRONOUS)
            except Exception:
                pass
        gl.glClearColor(0.1, 0.1, 0.1, 1.0)
        self.shaders.initialize()

    def resize(self, width: int, height: int) -> None:
        self._width = max(width, 1)
        self._height = max(height, 1)
        gl.glViewport(0, 0, self._width, self._height)

    def draw(self, render_scene: RenderScene, camera: CameraState) -> None:
        with FrameTimer(self.stats):
            self.stats.reset()
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

            ctx = PassContext(
                render_scene=render_scene,
                camera=camera,
                view_matrix=self._build_view_matrix(camera),
                projection_matrix=self._build_projection_matrix(),
                shaders=self.shaders,
                state_manager=self.state_manager,
                stats=self.stats,
            )
            for render_pass in self._passes:
                render_pass.execute(ctx)

    def highlight(self, node_paths: Sequence[str]) -> None:
        self._selection_pass.set_selected(node_paths)

    def hover(self, node_path: Optional[str]) -> None:
        self._selection_pass.set_hover(node_path)

    def frame(self, bounding_box, camera: CameraState) -> None:
        if not bounding_box:
            camera.reset()
            return
        corners = np.array(bounding_box)
        center = corners.mean(axis=0)
        half_extent = float(np.max(corners.max(axis=0) - corners.min(axis=0)) / 2.0)
        camera.pan_x = -float(center[0])
        camera.pan_y = -float(center[1])
        camera.zoom = min(camera.max_zoom, max(camera.min_zoom, 1.0 / max(half_extent, 1e-6)))

    def pick(self, screen_x, screen_y, viewport_width, viewport_height, camera, render_scene: RenderScene,
             mode: SelectionMode = SelectionMode.OBJECT) -> PickingResult:
        """
        Performs ray picking using vectorized triangle intersection.

        Selection is resolved against actual triangle geometry rather than
        bounding boxes, providing accurate object and face hits. Edge and vertex
        selection modes are not implemented yet. The current full scene triangle
        scan is suitable for inspection workloads but would require a spatial
        index for very large meshes.
        """
        if (viewport_width <= 0 or viewport_height <= 0 or not render_scene.node_ranges
                or not render_scene.meshes or render_scene.meshes[0].vertices.size == 0):
            return PickingResult()

        mesh = render_scene.meshes[0]
        vertices = mesh.vertices
        indices = mesh.indices
        if indices.size < 3:
            return PickingResult()

        mvp = self._build_projection_matrix() @ self._build_view_matrix(camera)
        try:
            inv_mvp = np.linalg.inv(mvp)
        except np.linalg.LinAlgError:
            return PickingResult()

        ndc_x = (2.0 * screen_x / viewport_width) - 1.0
        ndc_y = 1.0 - (2.0 * screen_y / viewport_height)
        near_point = self._unproject(inv_mvp, ndc_x, ndc_y, -1.0)
        far_point = self._unproject(inv_mvp, ndc_x, ndc_y, 1.0)
        ray_dir = far_point - near_point
        ray_dir /= max(np.linalg.norm(ray_dir), 1e-9)

        hit = self._ray_triangles_intersect(near_point, ray_dir, vertices, indices)
        if hit is None:
            return PickingResult()
        t, global_tri_index = hit
        hit_point = tuple((near_point + ray_dir * t).tolist())

        for node_range in render_scene.node_ranges:
            start_tri = node_range.index_start // 3
            count_tri = node_range.index_count // 3
            if start_tri <= global_tri_index < start_tri + count_tri:
                return PickingResult(
                    path=node_range.path, hit_point=hit_point,
                    face_index=global_tri_index - start_tri,
                )
        return PickingResult()

    @staticmethod
    def _ray_triangles_intersect(origin: np.ndarray, direction: np.ndarray,
                                  vertices: np.ndarray, indices: np.ndarray) -> Optional[Tuple[float, int]]:
        """
        Vectorized Möller-Trumbore against every triangle at once
        Returns:
             (t, global_triangle_index) for the nearest hit, or None.
        """
        tri = indices.reshape(-1, 3)
        v0 = vertices[tri[:, 0]]
        v1 = vertices[tri[:, 1]]
        v2 = vertices[tri[:, 2]]
        edge1 = v1 - v0
        edge2 = v2 - v0

        h = np.cross(direction, edge2)
        a = np.einsum("ij,ij->i", edge1, h)
        epsilon = 1e-9
        valid = np.abs(a) > epsilon
        f = np.zeros_like(a)
        f[valid] = 1.0 / a[valid]

        s = origin - v0
        u = f * np.einsum("ij,ij->i", s, h)
        valid &= (u >= 0.0) & (u <= 1.0)

        q = np.cross(s, edge1)
        v = f * np.einsum("j,ij->i", direction, q)
        valid &= (v >= 0.0) & (u + v <= 1.0)

        t = f * np.einsum("ij,ij->i", edge2, q)
        valid &= t > epsilon

        if not np.any(valid):
            return None
        candidate_t = np.where(valid, t, np.inf)
        best_index = int(np.argmin(candidate_t))
        best_t = float(candidate_t[best_index])
        if not np.isfinite(best_t):
            return None
        return best_t, best_index

    @staticmethod
    def _unproject(inv_mvp: np.ndarray, ndc_x: float, ndc_y: float, ndc_z: float) -> np.ndarray:
        clip = np.array([ndc_x, ndc_y, ndc_z, 1.0])
        world = inv_mvp @ clip
        world /= world[3]
        return world[:3]

    def destroy(self) -> None:
        for render_pass in self._passes:
            destroy = getattr(render_pass, "destroy", None)
            if destroy is not None:
                destroy()
        self.shaders.destroy()

    # Build the view transform explicitly for the core profile pipeline.
    # The resulting matrix matches the previous camera convention
    # LookAt applied first, followed by the X and Y rotations in order.
    def _build_view_matrix(self, camera: CameraState) -> np.ndarray:
        eye = np.array([
            camera.position[0] + camera.pan_x,
            camera.position[1] + camera.pan_y,
            camera.position[2] / camera.zoom,
        ], dtype=np.float64)
        look_at = self._look_at(eye, target=np.zeros(3), up=np.array([0.0, 1.0, 0.0]))
        rotate_x = self._rotation_matrix(camera.angle_x, axis=np.array([1.0, 0.0, 0.0]))
        rotate_y = self._rotation_matrix(camera.angle_y, axis=np.array([0.0, 1.0, 0.0]))
        return look_at @ rotate_x @ rotate_y

    def _build_projection_matrix(self) -> np.ndarray:
        """Reproduces gluPerspective(45, width/height, 0.1, 100000)."""
        fov_y = np.radians(45.0)
        aspect = self._width / self._height
        near, far = 0.1, 100000.0
        f = 1.0 / np.tan(fov_y / 2.0)
        return np.array([
            [f / aspect, 0.0, 0.0, 0.0],
            [0.0, f, 0.0, 0.0],
            [0.0, 0.0, (far + near) / (near - far), (2.0 * far * near) / (near - far)],
            [0.0, 0.0, -1.0, 0.0],
        ], dtype=np.float64)

    @staticmethod
    def _look_at(eye: np.ndarray, target: np.ndarray, up: np.ndarray) -> np.ndarray:
        forward = target - eye
        forward = forward / np.linalg.norm(forward)
        side = np.cross(forward, up)
        side = side / np.linalg.norm(side)
        recomputed_up = np.cross(side, forward)

        matrix = np.identity(4, dtype=np.float64)
        matrix[0, :3] = side
        matrix[1, :3] = recomputed_up
        matrix[2, :3] = -forward
        matrix[0, 3] = -np.dot(side, eye)
        matrix[1, 3] = -np.dot(recomputed_up, eye)
        matrix[2, 3] = np.dot(forward, eye)
        return matrix

    @staticmethod
    def _rotation_matrix(angle_degrees: float, axis: np.ndarray) -> np.ndarray:
        angle = np.radians(angle_degrees)
        x, y, z = axis
        c, s = np.cos(angle), np.sin(angle)
        t = 1.0 - c
        return np.array([
            [t*x*x + c,   t*x*y - s*z, t*x*z + s*y, 0.0],
            [t*x*y + s*z, t*y*y + c,   t*y*z - s*x, 0.0],
            [t*x*z - s*y, t*y*z + s*x, t*z*z + c,   0.0],
            [0.0,          0.0,         0.0,         1.0],
        ], dtype=np.float64)