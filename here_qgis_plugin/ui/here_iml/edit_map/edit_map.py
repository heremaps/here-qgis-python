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
from ..message_bar import show_msg_bar_info


class EditMapDialog(EditDialog):
    BULK_EDIT: bool = False

    def clear(self):
        if self.editor.count_edited_features() > 0:
            self._clear()

    def closeEvent(self, event):
        if self.editor.count_edited_features() > 0:
            self._closeEvent(event)
        else:
            self.reject()

    def get_unflattened_layer(self):
        try:
            return self.editor.get_unflattened_layer()
        except Exception as e:
            show_error_msg_box(
                e,
                "Failed to unflatten the layer",
                parent=self,
                details=dict(
                    layer_id=self.editor.flattened_layer.id(),
                ),
            )

    def display(self, index=None):
        self._display_row(index)

    def _display_row(self, index=None):
        if index is None:
            index = self.feature_selector.currentIndex()
        self.editor.set_current_index(index)
        feature = self.editor.get_current_feature()
        self.populate_table(
            feature.attributes(), self.get_flattened_layer().fields().names()
        )
        self.filter_table(self.search_bar.text())

    def populate_table(self, values, field_names):
        self.tableWidget.setRowCount(0)
        current_feature_updated_fields = self.editor.get_current_feature_edited_fields()
        for i, field in enumerate(field_names):
            if field in self.renamed_field_mapping:
                new_name = self.renamed_field_mapping[field]
                value = values[i]

                field_edited = (
                    True
                    if self.editor.reverse_lookup_field(new_name)
                    in current_feature_updated_fields
                    else False
                )

                row = 0 if field_edited else self.tableWidget.rowCount()
                self.tableWidget.insertRow(row)

                key_label = CopyableLabel(new_name)
                key_label.setToolTip(field)
                self.highlight_cell(key_label, field_edited)
                self.tableWidget.setCellWidget(row, 0, key_label)

                value_edit = QLineEdit(str(value))
                # signal for immediate coloring
                value_edit.editingFinished.connect(
                    lambda label=key_label, value=value_edit: self.save_row(
                        label, value
                    )
                )
                value_edit.setClearButtonEnabled(True)
                self.highlight_cell(value_edit, field_edited)
                self.tableWidget.setCellWidget(row, 1, value_edit)

        self.tableWidget.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

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

            # TODO: refactor get_current_feature_original_value, parse_value_to_type
            #  into update_current_feature
            original_value = self.editor.get_current_feature_original_value(
                original_key
            )
            parsed_value = self.editor.parse_value_to_type(original_key, value)
            if parsed_value is not None:
                value_changed = original_value != parsed_value
                self.highlight_cell(key_widget, value_changed)
                self.highlight_cell(value_widget, value_changed)
                self.editor.update_current_feature(original_key, value, value_changed)
                feature = self.editor.get_current_feature()
                self.populate_table(
                    feature.attributes(), self.get_flattened_layer().fields().names()
                )
            else:
                value_widget.setText(str(original_value))
                QMessageBox.critical(
                    self, "Failed", f"Provided value has a wrong type: `{value}`"
                )

            self.current_save = 0

    def upload_data(self):
        unflattened_layer = self.get_unflattened_layer()
        self.get_flattened_layer()

        # Gather upload details
        layer_id = unflattened_layer.id()
        project_hrn = self.project_hrn
        feature_type = self.layer_id
        feature_ids = [str(f["id"]) for f in unflattened_layer.getFeatures()]
        feature_count = len(feature_ids)

        # Show confirmation message
        confirm = QMessageBox.question(
            self,
            "Confirm Upload",
            (
                "You are about to upload the following:\n\n"
                f"• QGIS Layer ID: {layer_id}\n"
                f"• Project HRN: {project_hrn}\n"
                f"• IML Layer: {feature_type}\n"
                f"• Number of Features: {feature_count}\n"
                f"• Feature IDs: {', '.join(feature_ids)}\n\n"
                "Do you want to continue?"
            ),
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
        )

        if confirm != QMessageBox.StandardButton.Ok:
            self.editor.remove_unflattened_layer()
            self.refresh_canvas()
            return  # User cancelled upload

        try:
            upload_mapmaking_processing(
                project_hrn=self.project_hrn,
                layer_id=self.layer_id,
                map_type="livemap",
                upload_layer=unflattened_layer.id(),
                upload_selected_only=False,
                upload_edited=True,
            )

            # for now assume upload was successful
            self.update_layer()

            show_msg_bar_info(
                title="Successful",
                msg=f"Layer '{unflattened_layer.name()}' uploaded successfully.",
            )

            # Remove the unflattened and flattened layer from the project
            self.editor.remove_unflattened_layer()
            self.editor.remove_flattened_layer()
            self.refresh_canvas()
            self.accept()

        except Exception as e:
            self.editor.remove_unflattened_layer()
            show_error_msg_box(
                e,
                "An error occurred while uploading the layer",
                parent=self,
                details=dict(
                    project_hrn=self.project_hrn,
                    mom_layer_id=self.layer_id,
                    map_type="livemap",
                    upload_layer_id=unflattened_layer.id(),
                ),
            )
