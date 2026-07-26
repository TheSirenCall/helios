"""
Tool for panning the camera by dragging with the middle mouse button
while holding Alt.
"""
from __future__ import annotations

from PySide6 import QtCore

from helios.tools.base import Tool


class PanTool(Tool):
    name = "pan"

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
                and event.buttons() == QtCore.Qt.MouseButton.MiddleButton):
            viewport.camera.pan_x += dx * 0.01
            viewport.camera.pan_y -= dy * 0.01
            viewport.update()

    def on_mouse_release(self, viewport, event) -> None:
        self._last_pos = None