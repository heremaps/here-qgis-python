###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os
from enum import Enum
from typing import Union

from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QHeaderView,
    QLineEdit,
    QTableWidgetItem,
)

from ....processing_toolbox.get_and_load import DEFAULT_IML_LAYERS as LAYERS
from ..base_edit.copyable_label import CopyableLabel
from ..error_msg import show_error_msg_box
from ..property.property_core import load_config_from_file
from .query_builder import QueryBuilder

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


class FieldNameFormat(Enum):
    LongName = 0
    ShortName = 1


# TODO: cleanup. maybe some inheritance from edit_dialog?
class QueryBuild(QDialog):
    query_to_send = pyqtSignal(str)

    def __init__(
        self,
        layer_id: str,
        query_builder: QueryBuilder,
        parent=None,
    ):
        QDialog.__init__(self, parent)
        self.filename = "FilterPreset_MapMaking.json"
        self.preset_path = os.path.join(self.get_preset_dir(), self.filename)
        self.load_ui()
        self.addFilterOptions()
        self.layer_id = layer_id
        self.current_preset_path = ""
        self.renamed_field_mapping = {}
        self.query_builder = query_builder
        self.populate_preset_dropdown()
        self.current_save = 0

    def load_ui(self):
        ui_path = os.path.join(os.path.dirname(__file__), "query_build.ui")
        uic.loadUi(ui_path, self)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.search_bar.textChanged.connect(self.filter_table)
        self.clearButton.clicked.connect(self.clear_query)
        self.buildButton.clicked.connect(self.build_query)
        self.presetDropdown.currentIndexChanged.connect(self.handle_load_preset)

    def addFilterOptions(self):
        insert_index = 1
        self.tableWidget.insertColumn(insert_index)
        self.tableWidget.setHorizontalHeaderItem(
            insert_index, QTableWidgetItem("Filter condition")
        )

    def clear_query(self):
        self.query_builder.clear()
        self.populate_table()

    def filter_table(self, text):
        text = text.strip().lower()
        for row in range(self.tableWidget.rowCount()):
            key_widget = self.tableWidget.cellWidget(row, 0)
            if isinstance(key_widget, CopyableLabel):
                key = key_widget.text().lower()
                match = text in key
                self.tableWidget.setRowHidden(row, not match)

    def clear_change(self, text, key_widget: CopyableLabel, value_widget: QLineEdit):
        if text == "" and self.query_builder.field_in_query(key_widget.text()):
            self.save_row(key_widget.text(), value_widget, None)

    def build_query(self):
        query = self.query_builder.build_query()
        self.query_to_send.emit(query)
        self.close()

    def populate_preset_dropdown(self):
        # Clear existing items
        self.presetDropdown.clear()

        display_items = ["Long name", "Short name"]

        # Add to dropdown
        self.presetDropdown.addItems(display_items)

        # select preset
        preset_idx = 1 if len(display_items) > 0 else 0
        self.presetDropdown.setCurrentIndex(preset_idx)

    def get_preset_dir(self):
        return os.path.normpath(os.path.join(MODULE_DIR, "../../../mapping_preset"))

    def get_renamed_field_mapping_from_file(
        self,
        preset_path: str = "",
        mode: FieldNameFormat = FieldNameFormat.LongName,
    ):
        matched_layer_keyword = next(
            (layer_type for layer_type in LAYERS if layer_type in self.layer_id),
            "",
        )

        if not preset_path or not os.path.exists(preset_path):
            matched_from_config_data = {}
        else:
            # Config exists: load and apply mapping
            validate_config_data = load_config_from_file(preset_path)
            matched_from_config_data = validate_config_data.get(
                matched_layer_keyword, {}
            )

        if mode == FieldNameFormat.LongName:
            self.rename_field_mapping = {
                field: field
                for field, details in matched_from_config_data.items()
                if details.get("checked", False)
            }
        else:
            self.rename_field_mapping = {
                field: details.get("new_name", field)
                for field, details in matched_from_config_data.items()
                if details.get("checked", False)
            }

        return self.rename_field_mapping

    def get_renamed_field_mapping(self, preset_path, mode: FieldNameFormat):
        try:
            return self.get_renamed_field_mapping_from_file(preset_path, mode)
        except Exception as e:
            show_error_msg_box(
                e,
                "Failed to get renamed field mapping",
                parent=self,
                details=dict(
                    preset_path=preset_path,
                ),
            )
            return {}

    def display(self):
        self.populate_table()
        # self.filter_table(self.search_bar.text())

    def highlight_cell(
        self, obj: Union[CopyableLabel, QLineEdit, QComboBox], color: bool
    ):
        if color:
            obj.setStyleSheet("margin-left: 5px; background: yellow;")
        else:
            obj.setStyleSheet("margin-left: 5px;")

    def sort_table(self, key):
        return self.query_builder.field_in_query(key)

    def populate_table(self):
        self.tableWidget.setRowCount(0)
        sorted_long_keys = sorted(
            sorted(self.rename_field_mapping, key=self.rename_field_mapping.get),
            key=self.sort_table,
            reverse=True,
        )
        for long_key in sorted_long_keys:
            short_key = self.rename_field_mapping[long_key]
            field_in_query = self.query_builder.field_in_query(long_key)
            row = self.tableWidget.rowCount()
            self.tableWidget.insertRow(row)

            key_label = CopyableLabel(short_key)
            self.highlight_cell(key_label, field_in_query)
            self.tableWidget.setCellWidget(row, 0, key_label)

            filter_to_show, value_to_show = self.query_builder.get_value(long_key)
            combo_current_index = 0
            combo = QComboBox(self.tableWidget)
            operators = self.query_builder.get_all_operators(long_key)
            combo.addItems(operators)

            if value_to_show:
                if filter_to_show and filter_to_show in operators:
                    combo_current_index = operators.index(filter_to_show)

            self.highlight_cell(combo, field_in_query)
            combo.setEditable(False)
            combo.setCurrentIndex(combo_current_index)
            self.tableWidget.setCellWidget(row, 1, combo)

            value_edit = QLineEdit(value_to_show)
            # signal for immediate coloring
            value_edit.editingFinished.connect(
                lambda key=long_key, value=value_edit, combo=combo: self.save_row(
                    key, value, combo
                )
            )
            value_edit.textChanged.connect(
                lambda text, label=key_label, value=value_edit: self.clear_change(
                    text, label, value
                )
            )
            value_edit.setClearButtonEnabled(True)
            self.highlight_cell(value_edit, field_in_query)
            self.tableWidget.setCellWidget(row, 2, value_edit)
        self.tableWidget.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

    def save_row(self, key: str, value: QLineEdit, combo: QComboBox):
        self.current_save += 1
        if self.current_save == 1:
            text = value.text()
            if text:
                self.query_builder.add_filter(key, (combo.currentText(), text))
            else:
                self.query_builder.remove_filter(key)
            self.populate_table()
            self.current_save = 0

    def handle_load_preset(self):
        selected_display = self.presetDropdown.currentText()
        mode = (
            FieldNameFormat.LongName
            if "long" in selected_display.lower()
            else FieldNameFormat.ShortName
        )
        self.renamed_field_mapping = self.get_renamed_field_mapping(
            self.preset_path, mode
        )
        self.display()
