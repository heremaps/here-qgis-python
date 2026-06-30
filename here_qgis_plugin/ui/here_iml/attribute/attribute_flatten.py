###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.core import QgsProject, QgsVectorLayer
from qgis.PyQt import QtWidgets

from ...here_qgis_processing.flatten_on_fly_processing import flatten_on_fly_processing
from ..error_msg import show_error_msg_box
from .base_attribute import BaseAttributeTable


class AttributeTableFlatten(BaseAttributeTable):
    def __init__(self, iface):
        super().__init__(iface, "attribute.ui")
        self.new_flattened_layer = None

        if not self.layer:
            QtWidgets.QMessageBox.warning(self, "Warning", "No active layer selected.")
            return

        if not isinstance(self.layer, QgsVectorLayer):
            QtWidgets.QMessageBox.warning(
                self, "Warning", "The active layer is not a vector layer."
            )
            return

        if self.layer.selectedFeatureCount() == 0:
            QtWidgets.QMessageBox.warning(self, "Warning", "No feature selected.")
            return

        self.flatten_layer()
        self.show_attribute_table()
        self.delete_layer()

    def flatten_layer(self):
        try:
            flatten_layer = flatten_on_fly_processing(layer=self.layer.id())
            self.new_flattened_layer = QgsProject.instance().mapLayer(
                flatten_layer["new_layer_id"]
            )
        except Exception as e:
            show_error_msg_box(
                e,
                "Failed to flatten the layer",
                parent=self,
                details=dict(
                    layer_id=self.layer.id(),
                    layer_name=self.layer.name(),
                ),
            )

    def show_attribute_table(self):
        renamed_fields = self.load_config_fields(self.new_flattened_layer)
        self.populate_table(
            self.new_flattened_layer,
            renamed_fields,
            list(self.new_flattened_layer.getFeatures()),
        )
        self.exec()

    def delete_layer(self):
        # confirm with the user before removing
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Remove Layer",
            (
                "Do you want to remove the active layer"
                f" '{self.new_flattened_layer.name()}'?"
            ),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )

        if confirm == QtWidgets.QMessageBox.Yes:
            QgsProject.instance().removeMapLayer(self.new_flattened_layer.id())
        else:
            QtWidgets.QMessageBox.information(
                self, "Cancelled", "Layer removal was cancelled."
            )
