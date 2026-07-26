"""
Qt item model that exposes a SceneGraph through the QAbstractItemModel
interface.

The model is a lightweight view over the SceneGraph, mapping its node
hierarchy directly into Qt's model view API.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt
from PySide6.QtGui import QIcon

from helios.scene.components.mesh import MeshComponent
from helios.scene.graph import SceneGraph
from helios.scene.node import SceneNode


class SceneTreeModel(QAbstractItemModel):
    def __init__(self, graph: Optional[SceneGraph] = None, parent=None):
        super().__init__(parent)
        self._graph = graph
        self._empty_root = SceneNode(name="")

    def set_scene(self, graph: Optional[SceneGraph]) -> None:
        self.beginResetModel()
        self._graph = graph
        self.endResetModel()

    def _root(self) -> SceneNode:
        return self._graph.root if self._graph is not None else self._empty_root

    def _row_of(self, node: SceneNode) -> int:
        if node.parent is None:
            return 0
        return node.parent.children.index(node)

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        parent_node = parent.internalPointer() if parent.isValid() else self._root()
        if row >= len(parent_node.children):
            return QModelIndex()
        return self.createIndex(row, column, parent_node.children[row])

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()
        node: SceneNode = index.internalPointer()
        if node.parent is None or node.parent is self._root():
            return QModelIndex()
        return self.createIndex(self._row_of(node.parent), 0, node.parent)

    def rowCount(self, parent=QModelIndex()):
        parent_node = parent.internalPointer() if parent.isValid() else self._root()
        return len(parent_node.children)

    def columnCount(self, parent=QModelIndex()):
        return 1

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        node: SceneNode = index.internalPointer()
        if role == Qt.DisplayRole:
            return node.name
        if role == Qt.DecorationRole:
            return QIcon.fromTheme("mesh" if node.has_component(MeshComponent) else "folder")
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def path_for_index(self, index: QModelIndex) -> Optional[str]:
        if not index.isValid():
            return None
        return index.internalPointer().path

    def index_for_path(self, path: str) -> QModelIndex:
        if self._graph is None:
            return QModelIndex()
        node = self._graph.find_by_path(path)
        if node is None or node is self._graph.root:
            return QModelIndex()
        return self.createIndex(self._row_of(node), 0, node)

    def node_for_index(self, index: QModelIndex) -> Optional[SceneNode]:
        return index.internalPointer() if index.isValid() else None