###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os
from abc import abstractmethod
from typing import Union

from qgis.core import QgsVectorLayer
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialog, QLineEdit, QMessageBox
from qgis.utils import iface
from requests import HTTPError

from here_qgis.api.mapprojects import MapProjectsAPI

from ....api_factory import create_api_for_ui
from ....processing_toolbox.layer_metadata import LayerMetadata
from ..base_edit.copyable_label import CopyableLabel
from ..bulk_edit.bulk_editor import BulkEditor
from ..edit_map.layer_editor import LayerEditor
from ..error_msg import show_error_msg_box
from ..property.preset import get_preset_dir, get_preset_path, get_preset_titles

# TODO: refactored in different file for better reusability
# get_preset_dir
# get_preset_titles
# populate_preset_dropdown
# handle_load_preset


class EditDialog(QDialog):
    BULK_EDIT: bool = False

    def __init__(self, layer: QgsVectorLayer, parent=None):
        super().__init__(parent)
        self.layer = layer
        self.project_hrn = LayerMetadata.get_project_hrn(layer)
        self.layer_id = LayerMetadata.get_layer_id(self.layer)
        self.renamed_field_mapping = {}
        self.current_preset_path = ""
        self.editor = None

        # when user change value but doesn't move cursor
        # and click close button right away
        # the `reject()` function is call.
        # after that `save_row()` is called
        # and we get NoneType error
        # that flags prevents from that
        self.rejected = False

        # when user type incorrect value (incorrect type) and press ENTER
        # `finishedEditing` signal is emitted twice, so `save_row`
        # function is called twice.
        # this variable prevents from that second save attempt
        self.current_save = 0

        if self.BULK_EDIT:
            self.editor = BulkEditor(self.layer)
        else:
            self.editor = LayerEditor(self.layer)

        self.get_flattened_layer()

        self.load_ui()
        self.populate_preset_dropdown()
        self.display()

    def load_ui(self):
        path = (
            "../bulk_edit/bulk_edit.ui" if self.BULK_EDIT else "../edit_map/edit_map.ui"
        )
        ui_path = os.path.join(os.path.dirname(__file__), path)
        uic.loadUi(ui_path, self)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        if not self.BULK_EDIT:
            self.feature_selector.addItems(self.editor.get_feature_labels())
            self.feature_selector.currentIndexChanged.connect(self.display)
        self.search_bar.textChanged.connect(self.filter_table)
        self.clearButton.clicked.connect(self.clear)
        self.uploadButton.clicked.connect(self.upload_data)
        self.presetDropdown.currentIndexChanged.connect(self.handle_load_preset)

    def populate_preset_dropdown(self):
        # Clear existing items
        self.presetDropdown.clear()

        dir_preset = get_preset_dir()
        title_map = get_preset_titles(dir_preset)

        display_items = ["--Not Selected--"]
        self.file_map = {}  # {display_text: actual_filename}

        for filename, title in title_map.items():
            display_text = title
            display_items.append(display_text)
            self.file_map[display_text] = filename

        # Add to dropdown
        self.presetDropdown.addItems(display_items)

        # select preset
        preset_idx = 1 if len(display_items) > 0 else 0
        self.presetDropdown.setCurrentIndex(preset_idx)

    def handle_load_preset(self):
        selected_display = self.presetDropdown.currentText()
        if selected_display:
            selected_file = self.file_map.get(selected_display, selected_display)
            full_path = get_preset_path(selected_file)
            self.current_preset_path = full_path
            print(f"Loading preset from: {full_path}")
            self.renamed_field_mapping = self.get_renamed_field_mapping(full_path)
            self.display()
            # self.display_row()

    @abstractmethod
    def display(self, index=None):
        raise NotImplementedError()

    def _clearChanges(self):
        self.editor.remove_flattened_layer()
        del self.editor
        if self.BULK_EDIT:
            self.editor = BulkEditor(self.layer)
        else:
            self.editor = LayerEditor(self.layer)
        self.get_flattened_layer()
        if self.current_preset_path:
            self.renamed_field_mapping = self.get_renamed_field_mapping(
                self.current_preset_path
            )
        self.display()

    @abstractmethod
    def clear(self):
        raise NotImplementedError()

    def _clear(self):
        reply = QMessageBox.question(
            self,
            "Clear",
            "Do you want to clear the changes?",
            QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._clearChanges()
            self.refresh_canvas()

    def _closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            "Cancel",
            "Do you want to cancel the changes?",
            QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.reject()
        else:
            event.ignore()

    def reject(self):
        if self.editor:
            self.editor.remove_flattened_layer()
            self.refresh_canvas()
        self.rejected = True
        super().reject()

    def get_flattened_layer(self):
        try:
            return self.editor.get_flattened_layer()
        except Exception as e:
            show_error_msg_box(
                e,
                "Failed to flatten the layer",
                parent=self,
                details=dict(
                    layer_id=self.layer.id,
                    layer_name=self.layer.name,
                ),
            )

    def get_renamed_field_mapping(self, preset_path):
        try:
            return self.editor.get_renamed_field_mapping(preset_path)
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

    def highlight_cell(self, obj: Union[CopyableLabel, QLineEdit], color: bool):
        if color:
            obj.setStyleSheet("margin-left: 5px; background: yellow;")
        else:
            obj.setStyleSheet("margin-left: 5px;")

    @abstractmethod
    def populate_table(self, values, field_names):
        raise NotImplementedError()

    def filter_table(self, text):
        text = text.strip().lower()
        for row in range(self.tableWidget.rowCount()):
            key_widget = self.tableWidget.cellWidget(row, 0)
            if isinstance(key_widget, CopyableLabel):
                key = key_widget.text().lower()
                match = text in key
                self.tableWidget.setRowHidden(row, not match)

    @abstractmethod
    def save_row(self, key_widget: CopyableLabel, value_widget: QLineEdit):
        raise NotImplementedError()

    def update_layer(self):
        self.editor.update_layer()

    @staticmethod
    def refresh_canvas():
        # TODO: use different approach
        # so no refresh() function was used
        if iface:
            iface.mapCanvas().refresh()

    @abstractmethod
    def upload_layer(self):
        raise NotImplementedError()

    @classmethod
    def try_create_dialog(cls, layer: QgsVectorLayer, parent):
        if not layer:
            QMessageBox.warning(parent, "Warning", "No active layer selected.")
            return
        if not isinstance(layer, QgsVectorLayer):
            QMessageBox.warning(
                parent, "Warning", "The active layer is not a vector layer."
            )
            return
        if layer.selectedFeatureCount() == 0:
            QMessageBox.warning(parent, "Warning", "No feature selected.")
            return

        project_hrn = LayerMetadata.get_project_hrn(layer)
        if not cls.check_edit_permission(project_hrn, parent):
            return

        cls.get_project_name(project_hrn)
        return cls(layer)

    @classmethod
    def get_map_projects_api(cls, project_hrn):
        return create_api_for_ui(MapProjectsAPI, project_hrn=project_hrn)

    @classmethod
    def get_project_name(cls, project_hrn):
        map_projects_api = cls.get_map_projects_api(project_hrn)
        cls.project_name = map_projects_api.get_project_name()

    @classmethod
    def check_edit_permission(cls, project_hrn: str, parent):
        map_projects_api = create_api_for_ui(MapProjectsAPI, project_hrn)

        try:
            if not map_projects_api.has_edit_permission():
                show_error_msg_box(
                    None,
                    f"You don't have permission to edit the project {project_hrn}",
                    details=dict(caller_hrn=map_projects_api.get_caller_hrn()),
                    parent=parent,
                )
                # self.reject()
                return False

            return True
        except HTTPError as e:
            if e.response.status_code == 401:
                show_error_msg_box(
                    None, "Token expired. Please login again.", parent=parent
                )
            else:
                show_error_msg_box(e, "Error occured.", parent=parent)
            return False
