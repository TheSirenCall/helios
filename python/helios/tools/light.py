"""
Tool for interactively repositioning the scene light by dragging with
the left mouse button while holding Ctrl.
"""
from __future__ import annotations

from PySide6 import QtCore

from helios.tools.base import Tool


class LightTool(Tool):
    name = "light"

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

        if event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier:
            viewport.camera.light_pos[0] += dx * 0.1
            viewport.camera.light_pos[1] -= dy * 0.1
            viewport.update()

    def on_mouse_release(self, viewport, event) -> None:
        self._last_pos = None