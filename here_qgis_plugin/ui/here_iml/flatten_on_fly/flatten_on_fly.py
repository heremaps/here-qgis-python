###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.core import QgsVectorLayer
from qgis.PyQt import QtWidgets

from ...here_qgis_processing.flatten_on_fly_processing import flatten_on_fly_processing
from ..error_msg import show_error_msg_box


class FlattenOnFly(QtWidgets.QDialog):
    def __init__(self, iface):
        super().__init__()

        self.iface = iface
        self.layer = self.iface.activeLayer()

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

        try:
            flatten_on_fly_processing(layer=self.layer.id())
            QtWidgets.QMessageBox.information(
                self, "Success", "Layer flattened successfully."
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
