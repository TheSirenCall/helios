from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QPushButton, QSpinBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import QLineEdit

class TimelineBar(QWidget):
    valueChanged = Signal(int)

    def __init__(self, min_frame=0, max_frame=100, parent=None):
        super().__init__(parent)
        self.min_frame = min_frame
        self.max_frame = max_frame
        self.value = min_frame
        self.setFixedHeight(12)
        self.setMouseTracking(True)

    def setRange(self, min_frame, max_frame):
        self.min_frame = min_frame
        self.max_frame = max_frame
        self.update()

    def setValue(self, value):
        self.value = max(self.min_frame, min(value, self.max_frame))
        self.update()
        self.valueChanged.emit(self.value)

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()

        painter.setBrush(QColor(60, 60, 60))
        painter.setPen(Qt.NoPen)
        painter.drawRect(rect)

        t = (self.value - self.min_frame) / max(1, (self.max_frame - self.min_frame))
        filled_width = int(rect.width() * t)

        painter.setBrush(QColor(120, 180, 255))
        painter.drawRect(0, 0, filled_width, rect.height())

    def mousePressEvent(self, event):
        self._set_from_pos(event.position().x())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._set_from_pos(event.position().x())

    def _set_from_pos(self, x):
        ratio = x / max(1, self.width())
        frame = self.min_frame + ratio * (self.max_frame - self.min_frame)
        self.setValue(int(frame))

def _make_frame_edit(value):
    edit = QLineEdit(str(value))
    edit.setFixedWidth(60)
    edit.setAlignment(Qt.AlignCenter)
    edit.setStyleSheet("""
        QLineEdit {
            background: #2b2b2b;
            color: #dddddd;
            border: 1px solid #444;
            border-radius: 3px;
            padding: 2px;
        }
    """)
    return edit

def _make_step_button(text):
    button = QPushButton(text)
    button.setFixedWidth(28)
    return button

class TimelineWidget(QWidget):
    frame_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.min_frame = 1
        self.max_frame = 100
        self.fps = 24

        self.start_edit = _make_frame_edit(self.min_frame)
        self.end_edit = _make_frame_edit(self.max_frame)

        self.timeline = TimelineBar(self.min_frame, self.max_frame)
        self.prev_button = _make_step_button("◀|")
        self.next_button = _make_step_button("|▶")
        self.play_button = QPushButton("▶")
        self.timer = QTimer(self)

        self.start_edit.editingFinished.connect(self.update_range)
        self.end_edit.editingFinished.connect(self.update_range)

        self.timeline.valueChanged.connect(self.on_frame_changed)
        self.prev_button.clicked.connect(lambda: self.step(-1))
        self.next_button.clicked.connect(lambda: self.step(1))
        self.play_button.clicked.connect(self.toggle_playback)
        self.timer.timeout.connect(self.next_frame)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        layout.addWidget(self.start_edit)
        layout.addWidget(self.timeline, 1)
        layout.addWidget(self.end_edit)
        layout.addWidget(self.prev_button)
        layout.addWidget(self.play_button)
        layout.addWidget(self.next_button)

        self.setFixedHeight(42)

    def set_frame_range(self, start, end):
        self.start_edit.setText(str(int(start)))
        self.end_edit.setText(str(int(end)))
        self.update_range()

    def set_fps(self, fps):
        """
        Sets the playback frame rate.

        Non positive values are ignored, preserving the current frame rate.
        """
        if not fps or fps <= 0:
            return
        self.fps = fps
        if self.timer.isActive():
            self.timer.start(int(1000 / self.fps))

    def update_range(self):
        try:
            self.min_frame = int(self.start_edit.text())
            self.max_frame = int(self.end_edit.text())
        except ValueError:
            return

        if self.max_frame <= self.min_frame:
            self.max_frame = self.min_frame + 1
            self.end_edit.setText(str(self.max_frame))

        self.timeline.setRange(self.min_frame, self.max_frame)
        self.timeline.setValue(self.min_frame)

    def on_frame_changed(self, frame):
        self.frame_changed.emit(frame)

    def step(self, delta):
        self.timeline.setValue(self.timeline.value + delta)

    def toggle_playback(self):
        if self.timer.isActive():
            self.timer.stop()
            self.play_button.setText("▶")
        else:
            self.timer.start(int(1000 / self.fps))
            self.play_button.setText("❚❚")

    def next_frame(self):
        current = self.timeline.value
        next_val = current + 1

        if next_val > self.max_frame:
            next_val = self.min_frame

        self.timeline.setValue(next_val)