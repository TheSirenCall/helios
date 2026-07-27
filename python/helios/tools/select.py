"""
Tool for selecting scene nodes by clicking in the viewport. Uses the
renderer's picking system to determine the selected node and updates the
application's selection state.

This is the default active tool.
"""
from __future__ import annotations

import logging

from PySide6 import QtCore

from helios.tools.base import Tool

logger = logging.getLogger(__name__)

_CLICK_DRAG_THRESHOLD_PX = 4


class SelectTool(Tool):
    name = "select"

    def __init__(self):
        self._press_pos = None
        self._hover_path = None

    def on_mouse_press(self, viewport, event) -> None:
        self._press_pos = event.position()

    def on_mouse_move(self, viewport, event) -> None:
        # Only update the hover state when no mouse buttons are pressed.
        # Dragging is handled by navigation or manipulation tools, so
        # re-running picking on every mouse move would be unnecessary.
        if event.buttons() != QtCore.Qt.MouseButton.NoButton:
            return
        render_scene = viewport.current_render_scene()
        result = viewport.renderer.pick(
            int(event.position().x()), int(event.position().y()),
            viewport.width(), viewport.height(), viewport.camera, render_scene,
        )
        if result.path != self._hover_path:
            self._hover_path = result.path
            logger.debug("SelectTool: hover -> %s", result.path)
            viewport.renderer.hover(result.path)
            viewport.update()

    def on_mouse_release(self, viewport, event) -> None:
        if self._press_pos is None:
            return
        moved = (event.position() - self._press_pos).manhattanLength()
        self._press_pos = None
        if moved > _CLICK_DRAG_THRESHOLD_PX:
            return

        render_scene = viewport.current_render_scene()
        result = viewport.renderer.pick(
            int(event.position().x()), int(event.position().y()),
            viewport.width(), viewport.height(), viewport.camera, render_scene,
        )
        logger.debug("SelectTool: pick() at %s -> %s", event.position(), result)

        modifiers = event.modifiers()
        current = list(viewport.selection_service.selected_paths)

        if modifiers & QtCore.Qt.KeyboardModifier.ShiftModifier:
            # Shift additive multi-selection.
            if result.path and result.path not in current:
                current.append(result.path)
            viewport.selection_service.set_selection(current)
        elif modifiers & QtCore.Qt.KeyboardModifier.ControlModifier:
            # Ctrl toggle membership.
            if result.path:
                if result.path in current:
                    current.remove(result.path)
                else:
                    current.append(result.path)
            viewport.selection_service.set_selection(current)
        else:
            # Plain click replace selection
            viewport.selection_service.set_selection([result.path] if result.path else [])

        logger.debug("SelectTool: selection now %s", viewport.selection_service.selected_paths)