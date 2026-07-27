"""
Main application window.

Owns the application's dockable workspace, menus, toolbar, status bar,
and shared application state. MainWindow is responsible for composing
the application, wiring together services and panels, and coordinating
high level application flow.

Business logic is delegated to commands, services, and the EventBus,
keeping UI components loosely coupled.
"""
from __future__ import annotations

import sys
from typing import Optional

from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import QDockWidget, QFileDialog, QMainWindow

from helios.commands.base import CommandStack
from helios.commands.scene_commands import LoadSceneCommand
from helios.core.application.context import ApplicationContext
from helios.core.events.events import FrameChanged, SceneClosed, SceneLoaded
from helios.gui.panels.asset_browser.panel import AssetBrowserPanel
from helios.gui.panels.diagnostics.panel import DiagnosticsPanel
from helios.gui.panels.inspector.panel import InspectorPanel
from helios.gui.panels.log_viewer.panel import LogViewerPanel
from helios.gui.panels.outliner.panel import OutlinerPanel
from helios.gui.panels.python_console.panel import PythonConsolePanel
from helios.gui.panels.statistics.panel import StatisticsPanel
from helios.gui.viewer import SceneViewport
from helios.gui.widgets import timeline as _timeline
from helios.scene.graph import SceneGraph


class MainWindow(QMainWindow):
    def __init__(self, context: Optional[ApplicationContext] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Helios Viewer")
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.context = context or ApplicationContext()
        self.registry = self.context.plugins
        self.commands = CommandStack()
        self.scene: Optional[SceneGraph] = None

        self.setStyleSheet(self.context.themes.stylesheet())

        self._build_central_widget()
        self._build_panels()
        self._build_menus()
        self._build_toolbar()
        self._build_status_bar()

        self.context.events.subscribe(FrameChanged, self._on_frame_changed_event)
        self.resize(1600, 900)

    def _build_central_widget(self) -> None:
        self.viewport = SceneViewport(
            self.registry.renderer("opengl"),
            self.context.events,
            self.context.selection,
            self.context.tools,
        )
        self.timeline = _timeline.TimelineWidget()
        self.timeline.frame_changed.connect(self.on_frame_changed)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.viewport)
        layout.addWidget(self.timeline)
        self.setCentralWidget(central)

    def _build_panels(self) -> None:
        """Every panel is constructed with only the services/EventBus it needs."""

        self.outliner_panel = OutlinerPanel(self.context.events, self.context.selection, self.commands)
        self.inspector_panel = InspectorPanel(self.context.events, self.commands)
        self.asset_browser_panel = AssetBrowserPanel(self.context.asset_browser, self.context.events)
        self.statistics_panel = StatisticsPanel(self.context.events)
        self.diagnostics_panel = DiagnosticsPanel(self.context.events)
        self.log_viewer_panel = LogViewerPanel(self.context.events)
        self.python_console_panel = PythonConsolePanel(self.context)
        self.python_console_panel.namespace.update({
            "viewport": self.viewport,
            "commands": self.commands,
            "window": self,
        })

        self._docks: dict[str, QDockWidget] = {}
        self._add_dock("Outliner", self.outliner_panel, QtCore.Qt.LeftDockWidgetArea)
        self._add_dock("Property Inspector", self.inspector_panel, QtCore.Qt.RightDockWidgetArea)
        self._add_dock("Asset Browser", self.asset_browser_panel, QtCore.Qt.BottomDockWidgetArea)
        self._add_dock("Statistics", self.statistics_panel, QtCore.Qt.RightDockWidgetArea)
        self._add_dock("Diagnostics", self.diagnostics_panel, QtCore.Qt.RightDockWidgetArea)
        self._add_dock("Log Viewer", self.log_viewer_panel, QtCore.Qt.BottomDockWidgetArea)
        self._add_dock("Python Console", self.python_console_panel, QtCore.Qt.BottomDockWidgetArea)

    def _add_dock(self, title: str, widget: QtWidgets.QWidget, area) -> None:
        dock = QDockWidget(title, self)
        dock.setObjectName(title.replace(" ", ""))
        dock.setWidget(widget)
        self.addDockWidget(area, dock)
        self._docks[title] = dock

    def _build_menus(self) -> None:
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction("Open Scene...", self.open_file_dialog)
        self._recent_menu = file_menu.addMenu("Recent Files")
        self._refresh_recent_files_menu()
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)

        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addAction("Undo", self.commands.undo)
        edit_menu.addAction("Redo", self.commands.redo)

        view_menu = menu_bar.addMenu("&View")
        # Populated after docks exist, below.

        tools_menu = menu_bar.addMenu("&Tools")
        tools_menu.addAction("Frame Selected", lambda: self.context.cameras.frame_selected(self.viewport))
        tools_menu.addAction("Frame All", lambda: self.context.cameras.frame_all(self.viewport))

        window_menu = menu_bar.addMenu("&Window")
        window_menu.addAction("Save Workspace...", self._save_workspace)
        window_menu.addAction("Load Workspace...", self._load_workspace)

        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction("About", lambda: self.context.notifications.info("Helios Viewer"))

        for title, dock in self._docks.items():
            view_menu.addAction(dock.toggleViewAction())

    def _build_toolbar(self) -> None:
        toolbar = self.addToolBar("Main")
        toolbar.addAction("Open Scene", self.open_file_dialog)
        toolbar.addAction("Reload", self._reload_current_scene)
        toolbar.addAction("Frame Selected", lambda: self.context.cameras.frame_selected(self.viewport))
        toolbar.addSeparator()
        toolbar.addAction("Play", self.timeline.toggle_playback)
        toolbar.addSeparator()
        # Wireframe/Grid/Axes are toggles the are not implemented yet
        for label in ("Wireframe", "Grid", "Axes"):
            action = toolbar.addAction(label)
            action.setCheckable(True)
            action.setChecked(True)

    def _build_status_bar(self) -> None:
        status_bar = self.statusBar()
        self._scene_status_label = QtWidgets.QLabel("No scene loaded")
        self._frame_status_label = QtWidgets.QLabel("Frame: -")
        self._selection_status_label = QtWidgets.QLabel("Selection: 0")
        self._renderer_status_label = QtWidgets.QLabel("Renderer: opengl")
        for label in (
            self._scene_status_label, self._frame_status_label,
            self._selection_status_label, self._renderer_status_label,
        ):
            status_bar.addPermanentWidget(label)

        self.context.events.subscribe(SceneLoaded, lambda e: self._scene_status_label.setText(e.path))
        self.context.events.subscribe(SceneClosed, lambda e: self._scene_status_label.setText("No scene loaded"))
        from helios.core.events.events import SelectionChanged
        self.context.events.subscribe(
            SelectionChanged,
            lambda e: self._selection_status_label.setText(f"Selection: {len(e.selected_paths)}"),
        )

    def open_file_dialog(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open Scene File", "", "USD Files (*.usd *.usda *.usdc *.usdz)"
        )
        if file_name:
            self.load_scene(file_name)

    def _reload_current_scene(self) -> None:
        if self.scene is not None and self.context.settings.get("recent_files"):
            self.load_scene(self.context.settings.get("recent_files")[0])

    def load_scene(self, file_path: str) -> None:
        try:
            importer = self.registry.importer_for(file_path)
        except ValueError as exc:
            self.context.notifications.error(str(exc))
            return

        command = LoadSceneCommand(
            path=file_path,
            importer=importer,
            apply_scene=lambda scene: self._apply_scene(scene, file_path),
            get_current_scene=lambda: self.scene,
        )
        try:
            self.commands.do(command)
        except Exception as exc:
            self.context.notifications.error(f"Failed to load scene: {exc}")

    def _apply_scene(self, scene: Optional[SceneGraph], file_path: Optional[str] = None) -> None:
        self.scene = scene
        self.viewport.set_scene(scene)
        if scene is None:
            self.context.events.publish(SceneClosed())
            return

        self.timeline.set_fps(scene.fps)
        self.timeline.set_frame_range(*scene.frame_range)
        if file_path is not None:
            self.context.settings.add_recent_file(file_path)
            self._refresh_recent_files_menu()
            self.context.events.publish(SceneLoaded(path=file_path, scene=scene))
            self.context.notifications.info(f"Loaded {file_path}")

    def _refresh_recent_files_menu(self) -> None:
        self._recent_menu.clear()
        for path in self.context.settings.get("recent_files", []):
            self._recent_menu.addAction(path, lambda p=path: self.load_scene(p))

    def on_frame_changed(self, frame) -> None:
        self.viewport.set_frame(frame)
        self.context.events.publish(FrameChanged(frame=frame))

    def _on_frame_changed_event(self, event: FrameChanged) -> None:
        self._frame_status_label.setText(f"Frame: {event.frame}")

    def _save_workspace(self) -> None:
        from helios.core.workspace import WorkspaceState
        state = WorkspaceState(
            name="default",
            window_geometry=WorkspaceState.encode_bytes(bytes(self.saveGeometry())),
            dock_layout=WorkspaceState.encode_bytes(bytes(self.saveState())),
            active_renderer="opengl",
            timeline_frame=self.viewport.current_frame,
        )
        self.context.workspaces.save(state)

    def _load_workspace(self, name: str = "default") -> None:
        try:
            state = self.context.workspaces.load(name)
        except FileNotFoundError:
            self.context.notifications.warning(f"No saved workspace named '{name}'")
            return
        if state.window_geometry:
            self.restoreGeometry(state.decode_bytes(state.window_geometry))
        if state.dock_layout:
            self.restoreState(state.decode_bytes(state.dock_layout))

    def closeEvent(self, event) -> None:
        self.viewport.cleanup()
        super().closeEvent(event)


USDViewerWindow = MainWindow

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())