"""
CameraService manages camera state and high-level navigation actions
such as framing selections, while the Renderer is responsible for the
projection and framing calculations. This keeps camera math centralized
and consistent with the active rendering backend.

The service operates on the viewport's current RenderScene instead of
caching its own copy of the rendered geometry.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np

from helios.core.camera import CameraState


class CameraService:
    def __init__(self):
        self._bookmarks: Dict[str, dict] = {}
        self._history: List[dict] = []

    def frame_all(self, viewport) -> None:
        self._push_history(viewport.camera)
        viewport.renderer.frame(viewport.scene.bounding_box if viewport.scene else None, viewport.camera)
        viewport.update()

    def frame_selected(self, viewport) -> None:
        """
        Frames the camera around the combined bounding box of the selected
        nodes using the current RenderScene, ensuring the view matches the
        geometry currently being rendered. Falls back to frame_all() when
        nothing is selected.
        """
        selected_paths = set(viewport.selection_service.selected_paths)
        render_scene = viewport.current_render_scene()
        if not selected_paths or not render_scene.meshes or render_scene.meshes[0].vertices.size == 0:
            self.frame_all(viewport)
            return

        vertices = render_scene.meshes[0].vertices
        chunks = [
            vertices[start:start + count]
            for path, start, count in render_scene.node_ranges
            if path in selected_paths and count > 0
        ]
        if not chunks:
            self.frame_all(viewport)
            return

        combined = np.concatenate(chunks, axis=0)
        box_min, box_max = combined.min(axis=0), combined.max(axis=0)
        bbox = [
            (box_min[0], box_min[1], box_min[2]), (box_max[0], box_min[1], box_min[2]),
            (box_max[0], box_max[1], box_min[2]), (box_min[0], box_max[1], box_min[2]),
            (box_min[0], box_min[1], box_max[2]), (box_max[0], box_min[1], box_max[2]),
            (box_max[0], box_max[1], box_max[2]), (box_min[0], box_max[1], box_max[2]),
        ]
        self._push_history(viewport.camera)
        viewport.renderer.frame(bbox, viewport.camera)
        viewport.update()

    def save_bookmark(self, name: str, camera: CameraState) -> None:
        self._bookmarks[name] = camera.snapshot()

    def load_bookmark(self, name: str, camera: CameraState) -> None:
        if name in self._bookmarks:
            camera.restore(self._bookmarks[name])

    def bookmark_names(self) -> List[str]:
        return list(self._bookmarks.keys())

    def _push_history(self, camera: CameraState, limit: int = 20) -> None:
        self._history.append(camera.snapshot())
        del self._history[:-limit]

    def go_back(self, camera: CameraState) -> None:
        if self._history:
            camera.restore(self._history.pop())