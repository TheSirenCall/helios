
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple

from helios.core.events.bus import Event
from helios.scene.graph import SceneGraph


@dataclass(frozen=True)
class SceneLoaded(Event):
    path: str
    # Carrying the SceneGraph itself lets panels like Statistics compute
    # mesh/vertex/triangle counts directly from the event instead of needing
    # a separate SceneService.
    scene: Optional[SceneGraph] = None


@dataclass(frozen=True)
class SceneClosed(Event):
    pass


@dataclass(frozen=True)
class SceneModified(Event):
    reason: str = ""


@dataclass(frozen=True)
class SelectionChanged(Event):
    selected_paths: Tuple[str, ...] = ()


@dataclass(frozen=True)
class FrameChanged(Event):
    frame: float


@dataclass(frozen=True)
class PlaybackStarted(Event):
    pass


@dataclass(frozen=True)
class PlaybackStopped(Event):
    pass


@dataclass(frozen=True)
class RendererChanged(Event):
    renderer_name: str


@dataclass(frozen=True)
class AssetImported(Event):
    path: str


@dataclass(frozen=True)
class AssetDeleted(Event):
    path: str


@dataclass(frozen=True)
class AssetUpdated(Event):
    path: str


@dataclass(frozen=True)
class LogMessage(Event):
    level: str
    message: str
    logger_name: str = ""
    timestamp: float = 0.0


@dataclass(frozen=True)
class ValidatorFinished(Event):
    validator_name: str
    errors: Tuple[str, ...] = ()
    warnings: Tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkspaceLoaded(Event):
    name: str


@dataclass(frozen=True)
class WorkspaceSaved(Event):
    name: str


@dataclass(frozen=True)
class ProjectOpened(Event):
    path: str


@dataclass(frozen=True)
class ProjectClosed(Event):
    pass


@dataclass(frozen=True)
class PluginLoaded(Event):
    plugin_name: str


@dataclass(frozen=True)
class SettingsChanged(Event):
    key: str
    value: Any = None


@dataclass(frozen=True)
class ThemeChanged(Event):
    theme_name: str


@dataclass(frozen=True)
class RenderStatsUpdated(Event):
    cpu_frame_ms: float = 0.0
    fps: float = 0.0
    draw_calls: int = 0
    triangles: int = 0
    vertices: int = 0
    buffer_uploads: int = 0
    uploaded_vertices: int = 0
    shader_switches: int = 0


@dataclass(frozen=True)
class ViewportModeChanged(Event):
    mode: str


@dataclass(frozen=True)
class OverlayToggled(Event):
    overlay: str
    enabled: bool