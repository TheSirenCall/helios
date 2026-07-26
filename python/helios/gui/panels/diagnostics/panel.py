"""
Displays diagnostics and scene health information for the current scene.

The panel is driven by EventBus events and SceneGraph data, keeping it
independent of the renderer and importer backends.

Reported results reflect only the checks that have been implemented.
Features that are not yet validated are not included in the report.
"""
from __future__ import annotations

from typing import List

from PySide6.QtWidgets import QLabel, QPlainTextEdit, QTabWidget, QVBoxLayout, QWidget

from helios.core.events.bus import EventBus
from helios.core.events.events import RenderStatsUpdated, SceneClosed, SceneLoaded
from helios.core.scene_health import SceneStats, compute_scene_stats


class DiagnosticsPanel(QWidget):
    def __init__(self, event_bus: EventBus, parent=None):
        super().__init__(parent)
        self._last_render_stats: RenderStatsUpdated = RenderStatsUpdated()

        self._summary_label = QLabel("No scene loaded.")
        self._summary_label.setWordWrap(True)

        self._report_view = QPlainTextEdit()
        self._report_view.setReadOnly(True)

        tabs = QTabWidget()
        summary_container = QWidget()
        summary_layout = QVBoxLayout(summary_container)
        summary_layout.addWidget(self._summary_label)
        summary_layout.addStretch(1)
        tabs.addTab(summary_container, "Summary")
        tabs.addTab(self._report_view, "Full Report")

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)

        event_bus.subscribe(SceneLoaded, self._on_scene_loaded)
        event_bus.subscribe(SceneClosed, self._on_scene_closed)
        event_bus.subscribe(RenderStatsUpdated, self._on_render_stats)

    def _on_render_stats(self, event: RenderStatsUpdated) -> None:
        self._last_render_stats = event

    def _on_scene_closed(self, _event) -> None:
        self._summary_label.setText("No scene loaded.")
        self._report_view.clear()

    def _on_scene_loaded(self, event: SceneLoaded) -> None:
        if event.scene is None:
            self._on_scene_closed(None)
            return
        stats = compute_scene_stats(event.scene)
        warnings, errors, suggestions = self._analyze(stats)

        health = "Healthy" if not errors and not warnings else ("Errors present" if errors else "Warnings present")
        self._summary_label.setText(
            f"<b>{health}</b> — {stats.mesh_count} meshes, {stats.triangle_count:,} triangles, "
            f"{stats.skinned_mesh_count} animated (CPU skinned), {len(errors)} error(s), "
            f"{len(warnings)} warning(s)."
        )
        self._report_view.setPlainText(self._render_report(stats, warnings, errors, suggestions))

    def _analyze(self, stats: SceneStats):
        warnings: List[str] = list(stats.import_warnings)
        errors: List[str] = []
        suggestions: List[str] = []

        if stats.mesh_count == 0:
            errors.append("Scene contains no renderable meshes.")

        if stats.skinned_mesh_count > 0:
            suggestions.append(
                f"{stats.skinned_mesh_count} mesh(es) are CPU skinned (UsdSkel evaluated in "
                f"Python, not on the GPU) expect playback to slow down noticeably as "
                f"skinned mesh/triangle count grows. GPU skinning is not implemented."
            )

        if stats.triangle_count > 2_000_000:
            suggestions.append(
                f"{stats.triangle_count:,} triangles is a lot for this renderer's current "
                f"immediate per-frame CPU-GPU path consider whether the full scene needs "
                f"to be visible at once."
            )

        if not stats.is_animated:
            suggestions.append("Scene has no time varying attributes; imported as a static single frame.")

        suggestions.append(
            "UV coordinates, image textures, and UsdShade/UsdPreviewSurface material "
            "bindings are not yet extracted or validated by this importer "
            "'missing textures'/'missing UVs' checks are not implemented."
        )

        return warnings, errors, suggestions

    @staticmethod
    def _render_report(stats: SceneStats, warnings: List[str], errors: List[str], suggestions: List[str]) -> str:
        lines = [
            "=== Scene Statistics ===",
            f"Scene nodes: {stats.node_count}",
            f"Meshes: {stats.mesh_count}",
            f"Vertices: {stats.vertex_count:,}",
            f"Triangles: {stats.triangle_count:,}",
            f"Materials: {stats.material_count} ({stats.vertex_colored_mesh_count} with vertex colors)",
            "",
            "=== Animation ===",
            f"Frame range: {stats.frame_range[0]:.2f} - {stats.frame_range[1]:.2f} @ {stats.fps} fps",
            f"Animated: {'yes' if stats.is_animated else 'no (static single frame)'}",
            f"Skinned meshes: {stats.skinned_mesh_count} (CPU evaluated)",
            "",
            "=== Memory ===",
            f"Estimated GPU mem: {stats.estimated_gpu_memory_bytes / (1024 * 1024):.2f} MB "
            f"(vertex/normal/color buffers and indices; excludes textures, not yet supported)",
            "",
            f"=== Errors ({len(errors)}) ===",
        ]
        lines.extend(f"  - {e}" for e in errors) if errors else lines.append("  (none)")
        lines.append("")
        lines.append(f"=== Warnings ({len(warnings)}) ===")
        lines.extend(f"  - {w}" for w in warnings) if warnings else lines.append("  (none)")
        lines.append("")
        lines.append(f"=== Suggestions ({len(suggestions)}) ===")
        lines.extend(f"  - {s}" for s in suggestions)
        return "\n".join(lines)