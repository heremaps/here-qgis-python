###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os

from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox

from here_qgis.platform.platform_auth import PlatformAuth
from here_qgis.platform.platform_credentials import Credentials

from ...utils.settings_manager import (
    clear_config_preset_path,
    clear_credential_path,
    get_credential_path,
    is_authenticated,
    save_credential_path,
)
from ..error_msg import show_error_msg_box


class Authenticate(QtWidgets.QDialog):
    def __init__(self, parent=None):
        """Constructor for the Authentication Widget."""
        super().__init__(parent)

        # Determine which UI to load based on token existence
        if is_authenticated():
            self.load_signout_ui()
        else:
            self.load_signin_ui()
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

    def load_signin_ui(self):
        """Load the authentication UI."""
        ui_path = os.path.join(os.path.dirname(__file__), "signin.ui")
        uic.loadUi(ui_path, self)

        # Get the saved credentials path and set it in the text field
        saved_path = get_credential_path()
        if saved_path:
            self.filePathLineEdit.setText(saved_path)

        # Connect buttons
        self.browseButton.clicked.connect(self.browseFile)
        self.submitButton.clicked.connect(self.submit)

    def load_signout_ui(self):
        """Load the signout UI."""
        ui_path = os.path.join(os.path.dirname(__file__), "signout.ui")
        uic.loadUi(ui_path, self)

        # Connect signout button
        self.signoutButton.clicked.connect(self.signout)

    def browseFile(self):
        """Open a file dialog to browse for a credentials file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Credentials File", "", "All Files (*.*)"
        )
        if file_path:
            self.filePathLineEdit.setText(file_path)

    def submit(self):
        """Authenticate the user using the selected credentials file."""
        file_path = (
            self.filePathLineEdit.text() or get_credential_path()
        )  # Use the saved path if input is empty

        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Error", "File does not exist.")
            return

        try:
            # Authenticate using HERE Platform
            platform_cred = Credentials.from_credentials_file(file_path)
            platform = PlatformAuth(platform_cred)
            token = platform.token

            if token:
                save_credential_path(file_path)
                QMessageBox.information(self, "Success", "Authentication successful!")
                self.accept()
                self.load_signout_ui()  # Switch to signout UI
            else:
                QMessageBox.warning(
                    self, "Failure", "Authentication failed. Invalid credentials."
                )
        except Exception as e:
            show_error_msg_box(
                e,
                "An error occured",
                parent=self,
            )

    def signout(self):
        """Clear the stored token and return to authentication UI."""
        QMessageBox.information(self, "Signed Out", "You have been signed out.")
        clear_credential_path()
        clear_config_preset_path()
        self.reject()
        self.load_signin_ui()  # Switch back to authentication UI
