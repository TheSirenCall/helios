"""
Commands that mutate SceneNode fields directly (rename, visibility,
lock). Each publishes SceneModified so the panels (Outliner, Statistics,
Viewport) can refresh through the EventBus rather than being told directly.
"""

from __future__ import annotations

from helios.commands.base import Command
from helios.core.events.bus import EventBus
from helios.core.events.events import SceneModified
from helios.scene.node import SceneNode


class RenameCommand(Command):
    label = "Rename"

    def __init__(self, node: SceneNode, new_name: str, event_bus: EventBus):
        self._node = node
        self._new_name = new_name
        self._old_name = node.name
        self._event_bus = event_bus

    def execute(self) -> None:
        self._node.name = self._new_name
        self._event_bus.publish(SceneModified(reason="rename"))

    def undo(self) -> None:
        self._node.name = self._old_name
        self._event_bus.publish(SceneModified(reason="rename"))


class SetVisibilityCommand(Command):
    label = "Set Visibility"

    def __init__(self, node: SceneNode, visible: bool, event_bus: EventBus):
        self._node = node
        self._new_value = visible
        self._old_value = node.visible
        self._event_bus = event_bus

    def execute(self) -> None:
        self._node.visible = self._new_value
        self._event_bus.publish(SceneModified(reason="visibility"))

    def undo(self) -> None:
        self._node.visible = self._old_value
        self._event_bus.publish(SceneModified(reason="visibility"))


class SetLockCommand(Command):
    label = "Set Lock"

    def __init__(self, node: SceneNode, locked: bool, event_bus: EventBus):
        self._node = node
        self._new_value = locked
        self._old_value = node.locked
        self._event_bus = event_bus

    def execute(self) -> None:
        self._node.locked = self._new_value
        self._event_bus.publish(SceneModified(reason="lock"))

    def undo(self) -> None:
        self._node.locked = self._old_value
        self._event_bus.publish(SceneModified(reason="lock"))