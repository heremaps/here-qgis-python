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
from qgis.PyQt.QtWidgets import QHeaderView, QTableWidgetItem

from ....processing_toolbox.get_and_load import DEFAULT_IML_LAYERS as LAYERS
from ...utils.settings_manager import get_config_preset_path
from ..error_msg import show_error_msg_box
from ..property.property_core import load_config_from_file


class BaseAttributeTable(QtWidgets.QDialog):
    def __init__(self, iface, ui_file):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.layer = self.iface.activeLayer()
        self.load_ui(ui_file)

    def load_ui(self, ui_filename):
        ui_path = os.path.join(os.path.dirname(__file__), ui_filename)
        uic.loadUi(ui_path, self)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.closeButton.clicked.connect(self.reject)

    def load_config_fields(self, layer):
        matched_layer_keyword = next(
            (layer_type for layer_type in LAYERS if layer_type in layer.name().lower()),
            "",
        )
        config_file_path = get_config_preset_path()
        if not config_file_path or not os.path.exists(config_file_path):
            QtWidgets.QMessageBox.warning(
                self, "Warning", "No valid config file found."
            )
            return {}

        try:
            validate_config_data = load_config_from_file(config_file_path)
            matched_from_config_data = validate_config_data.get(
                matched_layer_keyword, {}
            )
            return {
                details["new_name"] if details["new_name"] else field: field
                for field, details in matched_from_config_data.items()
                if details.get("checked", False)
            }
        except Exception as e:
            show_error_msg_box(
                e,
                "Failed to load config",
                parent=self,
                details=dict(
                    config_file_path=config_file_path,
                ),
            )
            return {}

    def populate_table(self, layer, renamed_fields, features):
        field_indices = {field.name(): i for i, field in enumerate(layer.fields())}
        headers = [
            new
            for new in renamed_fields.keys()
            if field_indices.get(renamed_fields[new], -1) != -1
        ]
        field_indexes = {
            new: field_indices.get(orig, -1) for new, orig in renamed_fields.items()
        }

        self.tableWidget.setSortingEnabled(False)
        self.tableWidget.setColumnCount(len(headers))
        self.tableWidget.setRowCount(len(features))
        self.tableWidget.setHorizontalHeaderLabels(headers)

        for row_idx, feature in enumerate(features):
            attributes = feature.attributes()
            for col_idx, field_name in enumerate(headers):
                index = field_indexes[field_name]
                value = attributes[index] if index != -1 else "N/A"
                self.tableWidget.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))

        self.tableWidget.setSortingEnabled(True)
        self.tableWidget.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.tableWidget.horizontalHeader().setSectionsClickable(True)
