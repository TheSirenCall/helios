"""
Displays application log messages.

The panel is driven by LogMessage events and is independent of the
logging backend. It provides filtering and presentation of log output
without interacting directly with the logging system.
"""
from __future__ import annotations

import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QLineEdit, QPushButton,
    QTextEdit, QToolButton, QVBoxLayout, QWidget,
)

from helios.core.events.bus import EventBus
from helios.core.events.events import LogMessage

_LEVELS = ("ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

_LEVEL_COLORS = {
    "DEBUG": "#8a8a8a",
    "INFO": "#dddddd",
    "WARNING": "#e6b800",
    "ERROR": "#e05c5c",
    "CRITICAL": "#ff4040",
}

_MAX_LINES = 5000  # cap so an unattended long session doesn't grow unbounded


class LogViewerPanel(QWidget):
    def __init__(self, event_bus: EventBus, parent=None):
        super().__init__(parent)
        self._line_count = 0

        self._collapse_button = QToolButton()
        self._collapse_button.setCheckable(True)
        self._collapse_button.setChecked(True)
        self._collapse_button.setArrowType(Qt.ArrowType.DownArrow)
        self._collapse_button.setToolTip("Collapse/expand log")
        self._collapse_button.toggled.connect(self._on_collapse_toggled)

        self._level_filter = QComboBox()
        self._level_filter.addItems(_LEVELS)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Filter...")

        self._autoscroll = QCheckBox("Auto-scroll")
        self._autoscroll.setChecked(True)

        self._clear_button = QPushButton("Clear")
        self._clear_button.clicked.connect(self._on_clear)

        toolbar = QHBoxLayout()
        toolbar.addWidget(self._collapse_button)
        toolbar.addWidget(self._level_filter)
        toolbar.addWidget(self._search_box, 1)
        toolbar.addWidget(self._autoscroll)
        toolbar.addWidget(self._clear_button)

        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        layout = QVBoxLayout(self)
        layout.addLayout(toolbar)
        layout.addWidget(self._log_view)

        event_bus.subscribe(LogMessage, self._on_log_message)

    def _on_collapse_toggled(self, expanded: bool) -> None:
        self._collapse_button.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )
        self._log_view.setVisible(expanded)

    def _on_clear(self) -> None:
        self._log_view.clear()
        self._line_count = 0

    def _on_log_message(self, event: LogMessage) -> None:
        level_ok = self._level_filter.currentText() in ("ALL", event.level)
        text_ok = self._search_box.text().lower() in event.message.lower()
        if not (level_ok and text_ok):
            return

        timestamp = datetime.datetime.fromtimestamp(event.timestamp).strftime("%H:%M:%S.%f")[:-3] \
            if event.timestamp else "--:--:--.---"
        color = _LEVEL_COLORS.get(event.level, "#dddddd")

        # Reset lines occasionally rather than growing forever during a long session
        if self._line_count >= _MAX_LINES:
            cursor = self._log_view.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(
                cursor.MoveOperation.Down, cursor.MoveMode.KeepAnchor, _MAX_LINES // 4
            )
            cursor.removeSelectedText()
            self._line_count -= _MAX_LINES // 4

        escaped_message = (
            event.message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        self._log_view.append(
            f'<span style="color:#777777">{timestamp}</span> '
            f'<span style="color:{color}; font-weight:bold">[{event.level}]</span> '
            f'<span style="color:#999999">{event.logger_name}</span>: '
            f'<span style="color:{color}">{escaped_message}</span>'
        )
        self._line_count += 1

        if self._autoscroll.isChecked():
            scrollbar = self._log_view.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())