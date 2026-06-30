###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QKeySequence
from qgis.PyQt.QtWidgets import QApplication, QLabel


class CopyableLabel(QLabel):
    def __init__(self, text):
        super().__init__(text)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Copy):
            clipboard = QApplication.clipboard()
            clipboard.setText(self.text())
        else:
            super().keyPressEvent(event)
