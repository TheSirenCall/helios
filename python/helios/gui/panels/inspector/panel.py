"""
Displays and edits properties for the selected scene node.

The General section allows editing common node properties such as name,
visibility, and lock state. All changes are performed through the
command system to support undo and redo. Transform properties are
currently read only.

The panel can be extended with additional property editors.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QLabel, QLineEdit, QTabWidget, QVBoxLayout, QWidget

from helios.commands.base import CommandStack
from helios.commands.node_commands import SetLockCommand, SetVisibilityCommand, RenameCommand
from helios.core.events.bus import EventBus
from helios.core.events.events import SelectionChanged
from helios.scene.components.transform import TransformComponent
from helios.scene.graph import SceneGraph


class InspectorPanel(QWidget):
    def __init__(self, event_bus: EventBus, commands: CommandStack, parent=None):
        super().__init__(parent)
        self._event_bus = event_bus
        self._commands = commands
        self._graph: Optional[SceneGraph] = None
        self._current_path: Optional[str] = None
        self._current_frame: float = 0.0
        self._suppress_edits = False
        self._property_editor_factories: Dict[str, List[Callable[[], QWidget]]] = {}

        self._name_edit = QLineEdit()
        self._name_edit.setEnabled(False)
        self._name_edit.editingFinished.connect(self._on_name_edited)
        self._visible_check = QCheckBox("Visible")
        self._visible_check.setEnabled(False)
        self._visible_check.toggled.connect(self._on_visibility_toggled)
        self._locked_check = QCheckBox("Locked")
        self._locked_check.setEnabled(False)
        self._locked_check.toggled.connect(self._on_locked_toggled)

        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        general_layout.addWidget(QLabel("Name:"))
        general_layout.addWidget(self._name_edit)
        general_layout.addWidget(self._visible_check)
        general_layout.addWidget(self._locked_check)
        general_layout.addStretch(1)

        self._transform_label = QLabel("No selection.")
        self._metadata_label = QLabel("—")
        self._animation_label = QLabel("—")

        self._tabs = QTabWidget()
        self._tabs.addTab(general_tab, "General")
        self._tabs.addTab(self._wrap(self._transform_label), "Transform")
        self._tabs.addTab(self._wrap(self._metadata_label), "Metadata")
        self._tabs.addTab(self._wrap(self._animation_label), "Animation")

        layout = QVBoxLayout(self)
        layout.addWidget(self._tabs)

        event_bus.subscribe(SelectionChanged, self._on_selection_changed)

        from helios.core.events.events import SceneLoaded, SceneClosed, FrameChanged
        event_bus.subscribe(SceneLoaded, lambda e: setattr(self, "_graph", e.scene))
        event_bus.subscribe(SceneClosed, lambda e: setattr(self, "_graph", None))
        event_bus.subscribe(FrameChanged, lambda e: setattr(self, "_current_frame", e.frame))

    @staticmethod
    def _wrap(widget: QWidget) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(widget)
        layout.addStretch(1)
        return container

    def register_property_editor(self, tab_name: str, widget_factory: Callable[[], QWidget]) -> None:
        """
        Registers a property editor for the specified inspector tab.

        Allows additional editors to extend the inspector without modifying
        InspectorPanel.
        """
        self._property_editor_factories.setdefault(tab_name, []).append(widget_factory)

    def _on_selection_changed(self, event: SelectionChanged) -> None:
        self._suppress_edits = True
        try:
            if not event.selected_paths or self._graph is None:
                self._current_path = None
                self._name_edit.setText("")
                self._name_edit.setEnabled(False)
                self._visible_check.setEnabled(False)
                self._locked_check.setEnabled(False)
                self._transform_label.setText("No selection.")
                return

            if len(event.selected_paths) > 1:
                self._current_path = None
                self._name_edit.setText(f"{len(event.selected_paths)} items selected")
                self._name_edit.setEnabled(False)
                self._visible_check.setEnabled(False)
                self._locked_check.setEnabled(False)
                self._transform_label.setText("Multiple selection.")
                return

            path = event.selected_paths[0]
            node = self._graph.find_by_path(path)
            if node is None:
                return
            self._current_path = path
            self._name_edit.setText(node.name)
            self._name_edit.setEnabled(True)
            self._visible_check.setChecked(node.visible)
            self._visible_check.setEnabled(True)
            self._locked_check.setChecked(node.locked)
            self._locked_check.setEnabled(True)

            transform = node.get_component(TransformComponent)
            if transform is not None:
                matrix = transform.resolve_world_matrix(self._current_frame)
                translation = matrix[3, :3]
                self._transform_label.setText(f"Translation: {translation.round(4).tolist()}")
            else:
                self._transform_label.setText("No transform component.")
        finally:
            self._suppress_edits = False

    def _current_node(self):
        if self._graph is None or self._current_path is None:
            return None
        return self._graph.find_by_path(self._current_path)

    def _on_name_edited(self) -> None:
        if self._suppress_edits:
            return
        node = self._current_node()
        if node is not None and self._name_edit.text() != node.name:
            self._commands.do(RenameCommand(node, self._name_edit.text(), self._event_bus))

    def _on_visibility_toggled(self, checked: bool) -> None:
        if self._suppress_edits:
            return
        node = self._current_node()
        if node is not None and checked != node.visible:
            self._commands.do(SetVisibilityCommand(node, checked, self._event_bus))

    def _on_locked_toggled(self, checked: bool) -> None:
        if self._suppress_edits:
            return
        node = self._current_node()
        if node is not None and checked != node.locked:
            self._commands.do(SetLockCommand(node, checked, self._event_bus))