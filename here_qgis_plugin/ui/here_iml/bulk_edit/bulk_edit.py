###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


from qgis.PyQt.QtWidgets import QHeaderView, QLineEdit, QMessageBox

from ...here_qgis_processing.upload_mapmaking_processing import (
    upload_mapmaking_processing,
)
from ..base_edit.copyable_label import CopyableLabel
from ..base_edit.edit_dialog import EditDialog
from ..error_msg import show_error_msg_box


class BulkEditDialog(EditDialog):
    """Workflow:
    * User selects some features from original layer.
    * That original layer is flattened only to get flattened keys.
    * User makes edits in the edit dialog. Edits are save in
    in `BulkEditor.new_values` dict.
    * When user clicks Upload button, items from `new_values` dict
    are converted into unflattened dicts (Unflatten class is not used).
    * Those values are inserted directly into original layer.
    * After that, selected features from original layer are uploaded into MM.
    """

    BULK_EDIT: bool = True

    def clear(self):
        if self.editor.count_edits() > 0:
            self._clear()

    def closeEvent(self, event):
        if self.editor.count_edits() > 0:
            self._closeEvent(event)
        else:
            self.reject()

    def display(self, index=None):
        self.populate_table(None, self.get_flattened_layer().fields().names())
        self.filter_table(self.search_bar.text())

    def sort_table(self, field):
        new_name = self.renamed_field_mapping[field]
        return self.editor.was_value_edited(new_name)

    def populate_table(self, values, field_names):
        self.tableWidget.setRowCount(0)
        field_names = filter(
            lambda field: field in self.renamed_field_mapping, field_names
        )
        sorted_field_names = sorted(
            sorted(field_names), key=self.sort_table, reverse=True
        )
        for _, field in enumerate(sorted_field_names):
            new_name = self.renamed_field_mapping[field]
            field_edited = self.editor.was_value_edited(new_name)

            row = self.tableWidget.rowCount()
            self.tableWidget.insertRow(row)

            key_label = CopyableLabel(new_name)
            key_label.setToolTip(field)
            self.highlight_cell(key_label, field_edited)
            self.highlight_cell(key_label, field_edited)
            self.tableWidget.setCellWidget(row, 0, key_label)

            original_key = self.editor.reverse_lookup_field(new_name)
            value_to_show = self.editor.get_display_value(original_key)
            value_edit = QLineEdit(str(value_to_show))
            value_edit.setPlaceholderText(self.editor.string_field_type(original_key))
            # signal for immediate coloring
            value_edit.editingFinished.connect(
                lambda label=key_label, value=value_edit: self.save_row(label, value)
            )
            value_edit.textChanged.connect(
                lambda text, label=key_label, value=value_edit: self.clear_change(
                    text, label, value
                )
            )
            value_edit.setClearButtonEnabled(True)
            self.highlight_cell(value_edit, field_edited)
            self.highlight_cell(value_edit, field_edited)
            self.tableWidget.setCellWidget(row, 1, value_edit)

        self.tableWidget.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

    def clear_change(self, text, key_widget: CopyableLabel, value_widget: QLineEdit):
        if text == "" and self.editor.was_value_edited(key_widget.text()):
            self.save_row(key_widget, value_widget)

    def save_row(self, key_widget: CopyableLabel, value_widget: QLineEdit):
        self.current_save += 1
        if (
            not self.rejected
            and isinstance(key_widget, CopyableLabel)
            and isinstance(value_widget, QLineEdit)
            and self.current_save == 1
        ):
            renamed = key_widget.text()
            value = value_widget.text()

            original_key = self.editor.reverse_lookup_field(renamed)
            if not original_key:
                return

            if value == "":
                self.editor.reset_value(original_key)
                self.highlight_cell(key_widget, False)
                self.highlight_cell(value_widget, False)
                self.populate_table(None, self.get_flattened_layer().fields().names())
                self.current_save = 0
                return

            if self.editor.update_value(original_key, value):
                self.highlight_cell(key_widget, True)
                self.highlight_cell(value_widget, True)
                self.populate_table(None, self.get_flattened_layer().fields().names())
            else:
                text_to_set = str(self.editor.get_display_value(original_key))
                value_widget.setText(text_to_set)
                QMessageBox.critical(
                    self,
                    "Failed",
                    f"Provided wrong type for column: '{renamed}', value: '{value}'",
                )
            self.current_save = 0

    def confirm_pop_up(self) -> QMessageBox:
        confirm = QMessageBox(self)
        confirm.setIcon(QMessageBox.Icon.Question)
        confirm.setWindowTitle("Confirm Upload")
        confirm.setText(
            "You are about to upload the following:\n\n"
            f"• QGIS Layer name: {self.layer.name()}\n"
            f"• Project name: {self.project_name}\n"
            f"• IML Layer: {self.layer_id}\n"
            f"• Number of Features: {self.layer.selectedFeatureCount()}\n"
            "Do you want to continue?"
        )
        # confirm.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        confirm.addButton(QMessageBox.StandardButton.Ok)
        confirm.addButton(QMessageBox.StandardButton.Cancel)
        detailed_text = "You are about to update following fields:\n"
        for field in self.get_flattened_layer().fields().names():
            if field in self.renamed_field_mapping:
                new_name = self.renamed_field_mapping[field]
                if self.editor.was_value_edited(new_name):
                    detailed_text += f"{field}\n"
        confirm.setDetailedText(detailed_text)
        return confirm

    def upload_data(self):
        if self.editor.count_edits() == 0:
            QMessageBox.information(
                self,
                "No edits",
                "No edits were made. Upload will not proceed.",
            )
            return
        self.get_flattened_layer()

        # Show confirmation message
        confirm = self.confirm_pop_up()
        resp = confirm.exec()

        if resp != QMessageBox.StandardButton.Ok:
            self.refresh_canvas()
            return  # User cancelled upload

        try:
            self.update_layer()

            upload_mapmaking_processing(
                project_hrn=self.project_hrn,
                layer_id=self.layer_id,
                map_type="livemap",
                upload_layer=self.layer.id(),
                # I think it should be True, so changed
                upload_selected_only=True,
                upload_edited=True,
            )

            QMessageBox.information(
                self,
                "Successful",
                f"Layer '{self.layer.name()}' uploaded successfully.",
            )

            # Remove the unflattened and flattened layer from the project
            # self.editor.remove_unflattened_layer()
            self.editor.remove_flattened_layer()
            self.refresh_canvas()
            self.accept()

        except Exception as e:
            show_error_msg_box(
                error=e,
                message="An error occurred while uploading the layer",
                parent=self,
                details=dict(
                    project_hrn=self.project_hrn,
                    mom_layer_id=self.layer_id,
                    upload_layer_id=self.layer.id(),
                ),
            )
