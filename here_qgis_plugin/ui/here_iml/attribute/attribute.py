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

from .base_attribute import BaseAttributeTable


class AttributeTable(BaseAttributeTable):
    def __init__(self, iface, temp_renamed_fields=None):
        super().__init__(iface, "attribute.ui")

        if temp_renamed_fields:
            self.populate_table(
                self.layer, temp_renamed_fields, list(self.layer.getFeatures())
            )
            return

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

        renamed_fields = self.load_config_fields(self.layer)
        self.populate_table(self.layer, renamed_fields, self.layer.selectedFeatures())
