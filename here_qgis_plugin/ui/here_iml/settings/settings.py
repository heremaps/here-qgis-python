import os

from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialog, QMessageBox

from ....utils.clear_tmp import clear_tmp_directory
from ..message_bar import show_msg_bar_error, show_msg_bar_success


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Load UI
        self.load_ui()

        # Connect UI buttons
        self.btn_close.clicked.connect(self.close)
        self.btn_clear_tmp.clicked.connect(self.handle_clear_tmp)

    def load_ui(self):
        ui_path = os.path.join(os.path.dirname(__file__), "settings.ui")
        uic.loadUi(ui_path, self)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

    def handle_clear_tmp(self):
        reply = QMessageBox.question(
            self,
            "Confirm",
            "Are you sure you want to clear the Temporary Data Directory?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        try:
            clear_tmp_directory()
            show_msg_bar_success(
                msg="Temporary Data Directory cleared successfully", title="Success"
            )

        except Exception as e:
            show_msg_bar_error(
                msg=f"Failed to clear Temporary Data Directory: {e}", title="Error"
            )
