"""ZoomTool zooms via Alt+Right-drag or the scroll wheel."""
from __future__ import annotations

from PySide6 import QtCore

from helios.tools.base import Tool


class ZoomTool(Tool):
    name = "zoom"

    def __init__(self):
        self._last_pos = None

    def on_mouse_press(self, viewport, event) -> None:
        self._last_pos = event.position()

    def on_mouse_move(self, viewport, event) -> None:
        if self._last_pos is None:
            return
        dy = event.position().y() - self._last_pos.y()
        self._last_pos = event.position()

        if (event.modifiers() == QtCore.Qt.KeyboardModifier.AltModifier
                and event.buttons() == QtCore.Qt.MouseButton.RightButton):
            camera = viewport.camera
            camera.zoom = min(camera.max_zoom, max(camera.min_zoom, camera.zoom * (1.0 + dy * 0.01)))
            viewport.update()

    def on_mouse_release(self, viewport, event) -> None:
        self._last_pos = None

    def on_wheel(self, viewport, event) -> None:
        camera = viewport.camera
        camera.zoom = min(
            camera.max_zoom,
            max(camera.min_zoom, camera.zoom * (1.0 + event.angleDelta().y() * 0.001)),
        )
        viewport.update()