"""
UI for browsing assets.

The panel depends only on AssetBrowserService. Asset discovery and data
access are delegated to the service and its configured AssetProvider,
allowing the backing implementation to change without affecting the UI.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from helios.assets.browser.service import AssetBrowserService
from helios.assets.models.asset import Asset
from helios.core.events.bus import EventBus
from helios.core.events.events import AssetImported


class AssetBrowserPanel(QWidget):
    def __init__(self, service: AssetBrowserService, event_bus: EventBus, parent=None):
        super().__init__(parent)
        self._service = service
        self._event_bus = event_bus

        self._source_combo = QComboBox()
        self._source_combo.addItems(service.source_names())
        self._source_combo.currentTextChanged.connect(self._refresh)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search assets...")
        self._search_box.textChanged.connect(self._on_search_changed)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)

        layout = QVBoxLayout(self)
        layout.addWidget(self._source_combo)
        layout.addWidget(self._search_box)
        layout.addWidget(self._list)

        self._refresh()

    def _current_source(self) -> Optional[str]:
        return self._source_combo.currentText() or None

    def _refresh(self, *_args) -> None:
        source = self._current_source()
        if not source:
            self._list.clear()
            return
        self._populate(self._service.list_assets(source))

    def _on_search_changed(self, query: str) -> None:
        if not query:
            self._refresh()
            return
        self._populate(self._service.search(query, self._current_source()))

    def _populate(self, assets: list[Asset]) -> None:
        self._list.clear()
        for asset in assets:
            item = QListWidgetItem(f"[{asset.asset_type}] {asset.name}")
            item.setData(Qt.UserRole, asset)
            self._list.addItem(item)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        asset: Asset = item.data(Qt.UserRole)
        if asset.asset_type == "folder":
            self._populate(self._service.list_assets(self._current_source(), asset.path))
            return
        # Double clicking an asset publishes a load request. Import orchestration
        # is handled elsewhere, keeping the panel independent of application logic.
        self._event_bus.publish(AssetImported(path=asset.path))