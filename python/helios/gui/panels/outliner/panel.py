"""
Displays and interacts with the scene hierarchy.

Selection is synchronized through SelectionService, while scene
modifications are performed through the command system. The panel
remains independent of other UI components by communicating through
shared application services.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QItemSelectionModel, Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QLineEdit, QMenu, QTreeView, QVBoxLayout, QWidget,
)

from helios.commands.base import CommandStack
from helios.commands.node_commands import RenameCommand, SetLockCommand, SetVisibilityCommand
from helios.core.events.bus import EventBus
from helios.core.events.events import SceneClosed, SceneLoaded, SelectionChanged
from helios.core.selection import SelectionService
from helios.gui.models.outliner_filter_model import OutlinerFilterProxyModel
from helios.gui.models.scene_tree_model import SceneTreeModel


class OutlinerPanel(QWidget):
    def __init__(self, event_bus: EventBus, selection: SelectionService,
                 commands: CommandStack, parent=None):
        super().__init__(parent)
        self._event_bus = event_bus
        self._selection = selection
        self._commands = commands
        self._applying_external_selection = False

        self._model = SceneTreeModel()
        self._proxy = OutlinerFilterProxyModel()
        self._proxy.setSourceModel(self._model)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search...")
        self._search_box.textChanged.connect(self._proxy.setFilterFixedString)

        self._tree = QTreeView()
        self._tree.setModel(self._proxy)
        self._tree.setHeaderHidden(True)
        self._tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._tree.selectionModel().selectionChanged.connect(self._on_tree_selection_changed)

        layout = QVBoxLayout(self)
        layout.addWidget(self._search_box)
        layout.addWidget(self._tree)

        event_bus.subscribe(SceneLoaded, self._on_scene_loaded)
        event_bus.subscribe(SceneClosed, self._on_scene_closed)
        event_bus.subscribe(SelectionChanged, self._on_selection_changed_externally)

    def _on_scene_loaded(self, event: SceneLoaded) -> None:
        self._model.set_scene(event.scene)
        self._tree.expandAll()

    def _on_scene_closed(self, _event: SceneClosed) -> None:
        self._model.set_scene(None)

    def _on_selection_changed_externally(self, event: SelectionChanged) -> None:
        """Applies a selection that originated elsewhere (e.g. a
        viewport pick via SelectTool) to the tree, without re-publishing
        it (that would create an infinite Outliner <-> SelectionService
        loop)."""
        self._applying_external_selection = True
        try:
            selection_model = self._tree.selectionModel()
            selection_model.clearSelection()
            for path in event.selected_paths:
                source_index = self._model.index_for_path(path)
                if source_index.isValid():
                    proxy_index = self._proxy.mapFromSource(source_index)
                    selection_model.select(
                        proxy_index,
                        QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
                    )
        finally:
            self._applying_external_selection = False

    def _on_tree_selection_changed(self, *_args) -> None:
        if self._applying_external_selection:
            return
        paths = []
        for proxy_index in self._tree.selectionModel().selectedIndexes():
            source_index = self._proxy.mapToSource(proxy_index)
            path = self._model.path_for_index(source_index)
            if path:
                paths.append(path)
        self._selection.set_selection(paths)

    def _show_context_menu(self, pos) -> None:
        proxy_index = self._tree.indexAt(pos)
        if not proxy_index.isValid():
            return
        source_index = self._proxy.mapToSource(proxy_index)
        node = self._model.node_for_index(source_index)
        if node is None:
            return

        menu = QMenu(self)
        rename_action = menu.addAction("Rename...")
        visibility_action = menu.addAction("Hide" if node.visible else "Show")
        lock_action = menu.addAction("Lock" if not node.locked else "Unlock")
        chosen = menu.exec(self._tree.viewport().mapToGlobal(pos))

        if chosen is rename_action:
            self._rename_node(node)
        elif chosen is visibility_action:
            self._commands.do(SetVisibilityCommand(node, not node.visible, self._event_bus))
        elif chosen is lock_action:
            self._commands.do(SetLockCommand(node, not node.locked, self._event_bus))

    def _rename_node(self, node) -> None:
        from PySide6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(self, "Rename", "Name:", text=node.name)
        if ok and new_name and new_name != node.name:
            self._commands.do(RenameCommand(node, new_name, self._event_bus))