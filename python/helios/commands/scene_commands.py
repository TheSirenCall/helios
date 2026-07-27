"""
Commands that mutate which Scene the application currently has loaded.
"""

from __future__ import annotations

from typing import Callable, Optional

from helios.commands.base import Command
from helios.scene.graph import SceneGraph


class LoadSceneCommand(Command):
    label = "Load Scene"

    def __init__(
        self,
        path: str,
        importer,
        apply_scene: Callable[[Optional[SceneGraph]], None],
        get_current_scene: Callable[[], Optional[SceneGraph]],
    ):
        self._path = path
        self._importer = importer
        self._apply_scene = apply_scene
        self._get_current_scene = get_current_scene
        self._previous_scene: Optional[SceneGraph] = None

    def execute(self) -> None:
        self._previous_scene = self._get_current_scene()
        new_scene = self._importer.load(self._path)
        self._apply_scene(new_scene)

    def undo(self) -> None:
        self._apply_scene(self._previous_scene)