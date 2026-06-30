###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os
import shutil

from qgis.core import QgsProject, QgsVectorLayer
from qgis.PyQt import QtCore, QtWidgets, uic
from qgis.PyQt.QtWidgets import QHeaderView

from ....config import USER_PLUGIN_DIR
from ...utils.settings_manager import get_config_preset_path, save_config_preset_path
from ..attribute.attribute import AttributeTable
from ..error_msg import show_error_msg_box
from .property_core import (
    create_empty_config_file,
    load_config_from_file,
    update_config_file,
)

LAYERS = [
    "address",
    "building",
    "admin",
    "carto",
    "topology",
    "place",
    "relation",
]


class PropertyList(QtWidgets.QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())

        self.iface = iface
        self.config_data = {}  # Store loaded config
        self.layer_dict = {}
        self.config_file_path = get_config_preset_path()  # Load saved path
        self.layer = self.iface.activeLayer()
        # self.loaded_layers_list = []
        self.layer_name = ""
        self.loaded_layers_list = self.load_layers()

        if (
            not self.layer
            or not isinstance(self.layer, QgsVectorLayer)
            or "flatten" not in self.layer.name().lower()
        ):
            self.items_dict = {}
        else:
            self.items_dict = {
                field.name(): field.name() for field in self.layer.fields()
            }  # Original field names
            self.layer_name = self.layer.name()

        # if not isinstance(self.layer, QgsVectorLayer):
        #     QtWidgets.QMessageBox.warning(
        #         self, "Warning", "The active layer is not a vector layer."
        #     )
        #     return

        # if not self.loaded_layers_list:
        #     QtWidgets.QMessageBox.warning(
        #         self, "Warning", "No flatten layers found in the project."
        #     )
        #     return

        self.load_ui()

        # if self.config_file_path:
        #     self.load_from_store(self.config_file_path)

        if not self.config_file_path:
            # Create an empty configuration file if none exists
            create_empty_config_file(USER_PLUGIN_DIR, save_config_preset_path)
            self.config_file_path = get_config_preset_path()

        self.load_from_store(self.config_file_path)

        # self.populate_table()

    def load_ui(self):
        ui_path = os.path.join(os.path.dirname(__file__), "property.ui")
        uic.loadUi(ui_path, self)
        self.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)

        if any(layer in self.layer_name.lower() for layer in LAYERS):
            # Keep original name if it contains any known layer (case-insensitive)
            pass
        else:
            self.layer_name = "unknown"

        self.layerTypeLabel.setText(f"Layer Type: {self.identify_layer_type()}")

        # self.layerDropdown.addItems(self.loaded_layers_list)
        self.layerDropdown.addItems([""] + self.loaded_layers_list)
        self.layerDropdown.setCurrentText(self.layer_name)

        print("Loaded layers:", self.loaded_layers_list)

        # Connect buttons
        self.saveButton.clicked.connect(self.on_load_save)
        self.previewButton.clicked.connect(self.on_load_preview)
        self.cancelButton.clicked.connect(self.reject)
        self.searchBar.textChanged.connect(self.filter_table)
        self.importConfigButton.clicked.connect(self.load_config)
        self.exportConfigButton.clicked.connect(self.export_config)
        self.loadButton.clicked.connect(self.set_active_layer)

    def load_layers(self):
        """Load the layers from the QGIS project."""

        layers_list = list(QgsProject.instance().mapLayers().values())

        for layer in layers_list:
            if isinstance(layer, QgsVectorLayer):
                # Check if the layer name contains any value from LAYERS and "flatten"
                if (
                    any(layer_type in layer.name().lower() for layer_type in LAYERS)
                    and "flatten" in layer.name().lower()
                ):
                    self.layer_dict[layer.name()] = layer

        return list(self.layer_dict.keys())

    def set_active_layer(self):
        """Set the active layer based on the dropdown selection."""
        selected_layer_name = self.layerDropdown.currentText()
        if not selected_layer_name:
            QtWidgets.QMessageBox.warning(self, "Warning", "No layer selected.")
            return
        self.layer = self.layer_dict[selected_layer_name]
        self.layer_name = selected_layer_name

        self.iface.setActiveLayer(self.layer)

        self.items_dict = {field.name(): field.name() for field in self.layer.fields()}
        self.load_from_store(self.config_file_path)

        self.layerTypeLabel.setText(f"Layer Type: {self.identify_layer_type()}")

    def identify_layer_type(self):
        """Identify the layer type based on its name."""
        for layer in LAYERS:
            if layer in self.layer_name.lower():
                return layer
        return "unknown"

    def populate_table(self):
        """Populate the table with field names and checkboxes."""
        column_count = 3
        self.tableWidget.setColumnCount(column_count)
        self.tableWidget.setHorizontalHeaderLabels(
            ["Select", "Original Field", "New Field Name"]
        )
        self.tableWidget.setRowCount(len(self.items_dict))
        self.tableWidget.horizontalHeader().setStretchLastSection(True)
        self.tableWidget.setAlternatingRowColors(True)

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

            # Load from config if available
            if key in self.config_data:
                new_key_field.setText(self.config_data[key]["new_name"])
                checkbox.setChecked(self.config_data[key]["checked"])

            self.item_widgets.append((checkbox, key_label, new_key_field))

        # Set column 0 to fit content
        self.tableWidget.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )

        self.tableWidget.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Interactive
        )
        self.tableWidget.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )

        self.tableWidget.horizontalHeader().setStretchLastSection(False)

        QtCore.QTimer.singleShot(0, self.resize_columns)

    def resize_columns(self):
        """Resize columns 1 and 2 to 60% and 40% of available width."""
        total_width = self.tableWidget.viewport().width()
        self.tableWidget.setColumnWidth(1, int(total_width * 0.6))
        self.tableWidget.setColumnWidth(2, int(total_width * 0.4))

    def filter_table(self):
        """Filter table based on search bar input."""
        search_text = self.searchBar.text().lower()
        for row, (_checkbox, label, _field) in enumerate(self.item_widgets):
            self.tableWidget.setRowHidden(row, search_text not in label.text().lower())

    def on_load_preview(self):
        """Open the Feature Attribute Popup without saving."""
        selected_fields = {
            (
                text_field.text().strip() if text_field.text().strip() else label.text()
            ): label.text()
            for checkbox, label, text_field in self.item_widgets
            if checkbox.isChecked()  # Only include checked fields
        }

        if not selected_fields:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "No fields selected for preview."
            )
            return

        self.preview_window = AttributeTable(self.iface, selected_fields)

    def on_load_save(self):
        """Update the existing configuration file with new field mappings."""
        if not self.config_file_path:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "No configuration file loaded."
            )
            return
        if not self.items_dict:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "No fields available to save."
            )
            return

        # Save the updated configuration
        try:
            items = []
            matched_layer_keyword = next(
                (layer for layer in LAYERS if layer in self.layer.name().lower()), ""
            )
            for checkbox, label, text_field in self.item_widgets:
                original_name = label.text()
                new_name = text_field.text().strip()
                checked = checkbox.isChecked()
                items.append((original_name, new_name, checked))

            update_config_file(self.config_file_path, matched_layer_keyword, items)

            QtWidgets.QMessageBox.information(
                self, "Success", "Configuration updated successfully."
            )
        except Exception as e:
            show_error_msg_box(
                e,
                "Failed to upload config",
                parent=self,
                details=dict(
                    config_file_path=self.config_file_path,
                ),
            )

    def load_from_store(self, file_path):
        """Load field mappings from a JSON file."""

        matched_layer_keyword = next(
            (layer for layer in LAYERS if layer in self.layer_name.lower()), ""
        )

        if not file_path:
            return
        self.configPathLineEdit.setText(self.config_file_path)
        try:
            # with open(file_path, "r", encoding="utf-8") as file:
            #     data = json.load(file)
            #     self.config_data = data.get(matched_layer_keyword, {})
            data = load_config_from_file(file_path)
            self.config_data = data.get(matched_layer_keyword, {})
            self.config_file_path = file_path
            self.populate_table()
        except Exception as e:
            show_error_msg_box(
                e,
                "Failed to load config 3",
                parent=self,
                details=dict(
                    config_file_path=self.config_file_path,
                ),
            )
            if "No such file or directory" in str(e):
                create_empty_config_file(USER_PLUGIN_DIR, save_config_preset_path)
                self.config_file_path = get_config_preset_path()
                self.load_from_store(self.config_file_path)

    def load_config(self):
        """Load field mappings from a JSON file."""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load Config", "", "JSON Files (*.json)"
        )
        if not file_path:
            return

        # self.config_data = load_config_from_file(file_path)
        self.config_file_path = file_path
        self.configPathLineEdit.setText(file_path)  # Update text field
        save_config_preset_path(file_path)  # Persist file path
        self.load_from_store(file_path)
        # self.populate_table()

    def export_config(self):
        """Save a copy of the loaded JSON config file without modifications."""

        if not hasattr(self, "config_data") or not hasattr(self, "config_file_path"):
            QtWidgets.QMessageBox.warning(
                self, "Warning", "No configuration file loaded to export."
            )
            return

        # Prompt user for the new save location
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Config Copy", "", "JSON Files (*.json)"
        )
        if not file_path:
            return  # User canceled the save operation

        try:
            shutil.copy(self.config_file_path, file_path)

            QtWidgets.QMessageBox.information(
                self, "Success", "Configuration copied successfully."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to save config copy: {e}"
            )
            show_error_msg_box(
                e,
                "Failed to save config copy",
                parent=self,
                details=dict(
                    config_file_path=self.config_file_path,
                    file_path=file_path,
                ),
            )
