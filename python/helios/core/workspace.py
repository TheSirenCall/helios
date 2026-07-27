"""
Stores and restores named workspaces.

A workspace represents the complete UI state, including window layout,
renderer, camera, timeline position, and optionally the current
selection.

UI toolkit specific state is treated as opaque data. Callers are
responsible for capturing and restoring it, allowing this module to
remain independent of Qt.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from helios.core.events.bus import EventBus
from helios.core.events.events import WorkspaceLoaded, WorkspaceSaved


@dataclass
class WorkspaceState:
    name: str
    window_geometry: Optional[str] = None # base64 encoded QByteArray
    dock_layout: Optional[str] = None # base64 encoded QByteArray
    active_renderer: str = "opengl"
    camera: Dict[str, Any] = field(default_factory=dict)
    timeline_frame: float = 0.0
    selection: List[str] = field(default_factory=list)

    @staticmethod
    def encode_bytes(data: bytes) -> str:
        return base64.b64encode(data).decode("ascii")

    @staticmethod
    def decode_bytes(data: str) -> bytes:
        return base64.b64decode(data.encode("ascii"))


class WorkspaceManager:
    def __init__(self, directory: str, event_bus: Optional[EventBus] = None):
        self._directory = Path(directory)
        self._event_bus = event_bus

    def save(self, state: WorkspaceState) -> None:
        self._directory.mkdir(parents=True, exist_ok=True)
        path = self._directory / f"{state.name}.yaml"
        with path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(state.__dict__, handle)
        if self._event_bus is not None:
            self._event_bus.publish(WorkspaceSaved(name=state.name))

    def load(self, name: str) -> WorkspaceState:
        path = self._directory / f"{name}.yaml"
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        state = WorkspaceState(**data)
        if self._event_bus is not None:
            self._event_bus.publish(WorkspaceLoaded(name=name))
        return state

    def list_workspaces(self) -> List[str]:
        if not self._directory.is_dir():
            return []
        return sorted(p.stem for p in self._directory.glob("*.yaml"))