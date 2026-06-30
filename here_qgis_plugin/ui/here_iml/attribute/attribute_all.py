###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.core import QgsProject, QgsVectorLayer

from .base_attribute import LAYERS, BaseAttributeTable


class AttributeTableAll(BaseAttributeTable):
    def __init__(self, iface, temp_renamed_fields=None):
        super().__init__(iface, "attribute_all.ui")
        self.layer_dict = {}
        self.layer_name = self.layer.name() if self.layer else ""

        self.layerDropdown.addItems(self.load_layers())
        self.layerDropdown.setCurrentText(self.layer_name)

        self.loadButton.clicked.connect(self.set_active_layer)

        # if temp_renamed_fields:
        #     self.populate_table(self.layer, temp_renamed_fields, \
        # list(self.layer.getFeatures()))
        # else:
        self.set_active_layer()

    def load_layers(self):
        layers = QgsProject.instance().mapLayers().values()
        for layer in layers:
            if (
                isinstance(layer, QgsVectorLayer)
                and any(t in layer.name().lower() for t in LAYERS)
                and "flatten" in layer.name().lower()
            ):
                self.layer_dict[layer.name()] = layer
        return self.layer_dict.keys()

    def set_active_layer(self):
        selected = self.layerDropdown.currentText()
        self.layer = self.layer_dict.get(selected)
        self.layer_name = selected
        self.iface.setActiveLayer(self.layer)

        renamed_fields = self.load_config_fields(self.layer)
        self.populate_table(self.layer, renamed_fields, list(self.layer.getFeatures()))
