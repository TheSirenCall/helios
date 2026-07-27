"""
Base interface for viewport tools. The viewport forwards input events
to the active tool rather than implementing interaction logic itself,
keeping responsibilities separated and making new tools easy to add.

All event handlers are no ops by default, so tools only need to
override the events they handle.
"""
from __future__ import annotations


class Tool:
    name: str = "tool"

    def on_mouse_press(self, viewport, event) -> None:
        pass

    def on_mouse_move(self, viewport, event) -> None:
        pass

    def on_mouse_release(self, viewport, event) -> None:
        pass

    def on_wheel(self, viewport, event) -> None:
        pass

    def on_activate(self, viewport) -> None:
        pass

    def on_deactivate(self, viewport) -> None:
        pass