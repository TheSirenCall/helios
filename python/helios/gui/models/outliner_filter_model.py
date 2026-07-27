"""
Provides filtering for SceneTreeModel.

Keeping filtering separate from the model isolates search behavior from
the scene hierarchy and allows additional filtering capabilities to be
added without changing the model.
"""

from __future__ import annotations

from PySide6.QtCore import QSortFilterProxyModel, Qt


class OutlinerFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRecursiveFilteringEnabled(True)
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)