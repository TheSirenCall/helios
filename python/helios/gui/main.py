import sys
from pxr import Usd
from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import QPushButton, QFileDialog, QVBoxLayout, QDialog
from helios.gui import viewer as _main_viewer


class USDViewerWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("USD Viewer")
        self.setModal(False)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.viewer = _main_viewer.USDViewer()
        self.load_button = QPushButton("Load USD")
        self.load_button.clicked.connect(self.open_file_dialog)

        layout = QVBoxLayout()
        layout.addWidget(self.viewer)
        layout.addWidget(self.load_button)
        self.setLayout(layout)
        self.resize(1400, 700)

    def open_file_dialog(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open USD File", "", "USD Files (*.usd *.usda *.usdc)")
        if file_name:
            self.load_usd(file_name)

    def load_usd(self, file_path):
        try:
            usd_stage = Usd.Stage.Open(file_path)
            if not usd_stage:
                raise ValueError("Failed to open USD file.")
            self.viewer.usd_file = usd_stage
            self.viewer.vertices, self.viewer.normals, self.viewer.indices = self.viewer.extract_geometry(usd_stage)
            self.viewer.update()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to load USD file: {str(e)}")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = USDViewerWindow()
    window.show()
    sys.exit(app.exec())