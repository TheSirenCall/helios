"""
Extracts a RenderScene from a SceneGraph for a specific frame.

This is the boundary between the scene model and the renderer. The
renderer never accesses the SceneGraph directly and instead consumes the
RenderScene produced by this class, allowing different rendering
backends to be used without depending on scene graph internals.

The extractor caches the most recent (scene, frame) pair. If the same
scene and frame are requested again, the cached RenderScene is returned
without resampling. This preserves object identity for the underlying
numpy arrays, allowing downstream code to detect unchanged geometry and
skip GPU uploads.

The cache is keyed only by scene identity and frame. In place
modifications to the SceneGraph must call invalidate(), otherwise stale
data may be returned.
"""

from __future__ import annotations

from typing import Optional

from helios.core.render_scene import RenderableMesh, RenderScene
from helios.scene.graph import SceneGraph


class SceneExtractor:
    def __init__(self):
        self._cache_key: Optional[tuple] = None
        self._cache_value: Optional[RenderScene] = None

    def extract(self, scene: Optional[SceneGraph], frame: float) -> RenderScene:
        if scene is None:
            self._cache_key = None
            self._cache_value = None
            return RenderScene(frame=frame, meshes=[], bounding_box=None, node_ranges=[])

        key = (id(scene), frame)
        if key == self._cache_key:
            return self._cache_value

        vertices, normals, triangle_indices, node_ranges, colors = scene.sample(frame)
        render_scene = RenderScene(
            frame=frame,
            meshes=[RenderableMesh(
                name="scene", vertices=vertices, normals=normals,
                indices=triangle_indices, colors=colors,
            )],
            bounding_box=scene.bounding_box,
            node_ranges=node_ranges,
        )
        self._cache_key = key
        self._cache_value = render_scene
        return render_scene

    def invalidate(self) -> None:
        """
        Call after mutating a SceneGraph in place.

        The cache is keyed by scene identity and frame, so in place changes must
        be invalidated explicitly. Loading a new SceneGraph does not require
        invalidation because it has a different identity.
        """
        self._cache_key = None
        self._cache_value = None