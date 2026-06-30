###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os

from qgis.core import QgsVectorLayer
from qgis.PyQt import QtWidgets, uic

from .feature_popup import FeatureAttributePopup


# TODO: class not used. delete?
class FeatureList(QtWidgets.QDialog):
    def __init__(self, iface):
        super().__init__()

        self.iface = iface

        # Get field names from active layer
        layer = self.iface.activeLayer()
        if not layer:
            QtWidgets.QMessageBox.warning(self, "Warning", "No active layer selected.")
            return

        # Check if the layer is a vector layer
        if not isinstance(layer, QgsVectorLayer):
            QtWidgets.QMessageBox.warning(
                self, "Warning", "The active layer is not a vector layer."
            )
            return

        if layer.selectedFeatureCount() == 0:
            QtWidgets.QMessageBox.warning(self, "Warning", "No feature selected.")
            return

        # If there select feature not selected
        actionSelected = self.iface.actionSelect().isChecked()
        if not actionSelected:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "Select Feature tool is not active."
            )
            return

        self.load_ui()

        self.items_dict = {
            field.name(): field.name() for field in layer.fields()
        }  # Field names dictionary

        # Configure Table Widget
        self.tableWidget.setColumnCount(3)
        self.tableWidget.setHorizontalHeaderLabels(
            ["Select", "Original Field", "New Field Name"]
        )
        self.tableWidget.setRowCount(len(self.items_dict))
        self.tableWidget.horizontalHeader().setStretchLastSection(True)
        self.tableWidget.setAlternatingRowColors(True)

        # Populate Table
        self.item_widgets = []
        for row, (key, _value) in enumerate(self.items_dict.items()):
            # Checkbox
            checkbox = QtWidgets.QCheckBox()
            checkbox.setStyleSheet("margin-left: 10px;")
            self.tableWidget.setCellWidget(row, 0, checkbox)

            # Original Key Label
            key_label = QtWidgets.QLabel(key)
            key_label.setStyleSheet("margin-left: 5px;")
            self.tableWidget.setCellWidget(row, 1, key_label)

            # New Key Text Field
            new_key_field = QtWidgets.QLineEdit()
            new_key_field.setPlaceholderText("New field name...")
            new_key_field.setStyleSheet("padding: 0px 5px; border-style: none;")
            self.tableWidget.setCellWidget(row, 2, new_key_field)

            self.item_widgets.append((checkbox, key_label, new_key_field))

    def load_ui(self):
        ui_path = os.path.join(os.path.dirname(__file__), "feature.ui")
        uic.loadUi(ui_path, self)

        # Connect buttons and search bar
        self.loadButton.clicked.connect(self.on_load_clicked)
        self.cancelButton.clicked.connect(self.reject)
        self.searchBar.textChanged.connect(self.filter_table)

    def filter_table(self):
        """Filter the table based on the search bar input."""
        search_text = self.searchBar.text().lower()

        for row, (_checkbox, label, _field) in enumerate(self.item_widgets):
            if search_text in label.text().lower():
                self.tableWidget.setRowHidden(row, False)
            else:
                self.tableWidget.setRowHidden(row, True)

    def on_load_clicked(self):
        """Handle Load button: Collect selected field names and their index numbers."""
        selected_fields = {}

        for row, (checkbox, label, text_field) in enumerate(self.item_widgets):
            if checkbox.isChecked():
                new_name = text_field.text().strip()
                original_name = label.text()
                key = (
                    new_name if new_name else original_name
                )  # Use renamed or original field name
                selected_fields[key] = (
                    row  # Key = Selected field name, Value = Index number
                )

        if not selected_fields:  # If no fields are selected
            QtWidgets.QMessageBox.warning(
                self, "Warning", "No fields selected. Please select at least one field."
            )
            return  # Exit the method if nothing is selected

        # print("Selected Fields with Index:", selected_fields)

        # Open the Feature Popup with the selected fields
        feature_popup = FeatureAttributePopup(self.iface, selected_fields)
        feature_popup.exec()
