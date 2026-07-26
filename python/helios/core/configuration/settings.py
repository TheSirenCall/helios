"""
Persistent user settings. This is distinct from Configuration:
Configuration is (mostly) read-only, studio/project authored YAML.
SettingsManager is per-user, mutable, and written back to disk.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar

import yaml

from helios.core.events.bus import EventBus

T = TypeVar("T")

_DEFAULTS: Dict[str, Any] = {
    "recent_files": [],
    "window": {"geometry": None, "dock_layout": None},
    "viewport": {"background_color": [0.1, 0.1, 0.1]},
    "renderer": {"backend": "opengl"},
    "timeline": {"fps": 24.0, "loop": True},
    "camera": {"min_zoom": 0.05, "max_zoom": 50.0},
    "theme": {"name": "dark"},
}


class SettingsManager:

    def __init__(self, path: str, event_bus: Optional[EventBus] = None):
        self._path = Path(path)
        self._event_bus = event_bus
        self._data: Dict[str, Any] = dict(_DEFAULTS)
        self._load()

    def _load(self) -> None:
        if self._path.is_file():
            with self._path.open("r", encoding="utf-8") as handle:
                loaded = yaml.safe_load(handle) or {}
            self._data.update(loaded)

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(self._data, handle)

    def get(self, dotted_key: str, default: Optional[T] = None) -> T:
        node: Any = self._data
        for part in dotted_key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default  # type: ignore[return-value]
            node = node[part]
        return node

    def set(self, dotted_key: str, value: Any, persist: bool = True) -> None:
        parts = dotted_key.split(".")
        node = self._data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
        if persist:
            self.save()
        if self._event_bus is not None:
            from helios.core.events.events import SettingsChanged
            self._event_bus.publish(SettingsChanged(key=dotted_key, value=value))

    def add_recent_file(self, path: str, limit: int = 10) -> None:
        recents: List[str] = list(self.get("recent_files", []))
        if path in recents:
            recents.remove(path)
        recents.insert(0, path)
        self.set("recent_files", recents[:limit])