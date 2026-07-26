"""
Displays scene and rendering statistics.

Scene metrics are computed using the shared scene statistics service,
while renderer metrics are updated from RenderStatsUpdated events. This
keeps the panel independent of both scene traversal and rendering
implementation details.
"""
from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLabel, QWidget

from helios.core.events.bus import EventBus
from helios.core.events.events import (
    RenderStatsUpdated, SceneClosed, SceneLoaded, SelectionChanged,
)
from helios.core.scene_health import compute_scene_stats


class StatisticsPanel(QWidget):
    def __init__(self, event_bus: EventBus, parent=None):
        super().__init__(parent)
        self._rows: dict[str, QLabel] = {}

        layout = QFormLayout(self)
        for label in (
            "Scene Nodes", "Meshes", "Vertices", "Triangles", "Materials",
            "Vertex-Colored Meshes", "Animated Meshes", "Selection Count",
            "Draw Calls", "FPS", "GPU Memory (est.)",
        ):
            value_label = QLabel("N/A")
            self._rows[label] = value_label
            layout.addRow(f"{label}:", value_label)

        event_bus.subscribe(SceneLoaded, self._on_scene_loaded)
        event_bus.subscribe(SceneClosed, self._on_scene_closed)
        event_bus.subscribe(SelectionChanged, self._on_selection_changed)
        event_bus.subscribe(RenderStatsUpdated, self._on_render_stats)

    def _on_scene_loaded(self, event: SceneLoaded) -> None:
        if event.scene is None:
            self._on_scene_closed(None)
            return
        stats = compute_scene_stats(event.scene)

        self._rows["Scene Nodes"].setText(str(stats.node_count))
        self._rows["Meshes"].setText(str(stats.mesh_count))
        self._rows["Vertices"].setText(str(stats.vertex_count))
        self._rows["Triangles"].setText(str(stats.triangle_count))
        self._rows["Materials"].setText(str(stats.material_count))
        self._rows["Vertex-Colored Meshes"].setText(str(stats.vertex_colored_mesh_count))
        self._rows["Animated Meshes"].setText(str(stats.skinned_mesh_count))

    def _on_scene_closed(self, _event) -> None:
        for key in (
            "Scene Nodes", "Meshes", "Vertices", "Triangles", "Materials",
            "Vertex-Colored Meshes", "Animated Meshes",
        ):
            self._rows[key].setText("N/A")

    def _on_selection_changed(self, event: SelectionChanged) -> None:
        self._rows["Selection Count"].setText(str(len(event.selected_paths)))

    def _on_render_stats(self, event: RenderStatsUpdated) -> None:
        self._rows["Draw Calls"].setText(str(event.draw_calls))
        self._rows["FPS"].setText(f"{event.fps:.1f}")
        mb = (event.uploaded_vertices * 36) / (1024 * 1024) if event.uploaded_vertices else 0.0
        self._rows["GPU Memory (est.)"].setText(f"{mb:.2f} MB" if mb else "0.00 MB")