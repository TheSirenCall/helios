"""
OrbitTool allows the camera to be rotated by dragging with the left
mouse button while holding Alt.
"""
from __future__ import annotations

from PySide6 import QtCore

from helios.tools.base import Tool


class OrbitTool(Tool):
    name = "orbit"

    def __init__(self):
        self._last_pos = None

    def on_mouse_press(self, viewport, event) -> None:
        self._last_pos = event.position()

    def on_mouse_move(self, viewport, event) -> None:
        if self._last_pos is None:
            return
        dx = event.position().x() - self._last_pos.x()
        dy = event.position().y() - self._last_pos.y()
        self._last_pos = event.position()

        if (event.modifiers() == QtCore.Qt.KeyboardModifier.AltModifier
                and event.buttons() == QtCore.Qt.MouseButton.LeftButton):
            viewport.camera.angle_x += dy * 0.5
            viewport.camera.angle_y += dx * 0.5
            viewport.update()

    def on_mouse_release(self, viewport, event) -> None:
        self._last_pos = None