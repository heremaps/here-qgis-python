###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import traceback
from typing import Optional

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QMessageBox, QWidget


def show_error_msg_box(
    error: Exception,
    message: str = "",
    parent: Optional[QWidget] = None,
    details: Optional[dict] = None,
):
    """Shows error message in QMessageBox.
    Detailed text includes `traceback` and key value pairs `details` for troubleshooting
    """
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setWindowTitle("Error")
    if error:
        msg_error = repr(error)
        detailed_text = str(
            traceback.format_exc(),
        )

        if message:
            text = f"{message}: {msg_error}"
        else:
            text = msg_error
    else:
        msg_error = ""
        detailed_text = ""
        text = message

    msg.setText(text)
    if details:
        for key, val in details.items():
            detailed_text += f"{key} = {val}\n"

    msg.setDetailedText(detailed_text)
    msg.setWindowModality(Qt.WindowModality.ApplicationModal)
    msg.show()
