"""
Provides an embedded Python console.

The console executes scripts within an application namespace populated
by MainWindow. ApplicationContext provides access to application
services, while additional objects can be exposed as needed.
"""
from __future__ import annotations

import io
import contextlib
from typing import Any, Dict

from PySide6.QtWidgets import QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget

from helios.core.application.context import ApplicationContext


class PythonConsolePanel(QWidget):
    def __init__(self, context: ApplicationContext, parent=None):
        super().__init__(parent)
        self.namespace: Dict[str, Any] = {"context": context}

        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._input = QLineEdit()
        self._input.setPlaceholderText(">>> ")
        self._input.returnPressed.connect(self._run_current_line)

        layout = QVBoxLayout(self)
        layout.addWidget(self._output)
        layout.addWidget(self._input)

    def _run_current_line(self) -> None:
        code = self._input.text()
        self._input.clear()
        self._output.appendPlainText(f">>> {code}")

        buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer):
                try:
                    result = eval(code, self.namespace)
                    if result is not None:
                        print(repr(result))
                except SyntaxError:
                    exec(code, self.namespace)
        except Exception as exc:
            buffer.write(f"{type(exc).__name__}: {exc}\n")

        output_text = buffer.getvalue()
        if output_text:
            self._output.appendPlainText(output_text.rstrip("\n"))