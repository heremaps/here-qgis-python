###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.core import QgsLayerTreeLayer, QgsProject

from .iml_reload_many_layers import ReloadManyIMLLayers
from .processing_utils import LayerGroupPostProcessor


class ReloadAllVisibleLayers(ReloadManyIMLLayers):
    @classmethod
    def createInstance(cls):
        return cls()

    def displayName(self) -> str:
        return "IML: Reload All Visible Layers"

    def initAlgorithm(self, configuration=None):
        return super().initAlgorithm(configuration)

    def processAlgorithm(self, parameters, context, feedback):
        invalid_status = self._check_invalid_credentials(parameters, feedback)
        if invalid_status:
            return invalid_status

        visible_layers = self.filterVisibleLayers(
            QgsProject.instance().mapLayers().values()
        )

        if visible_layers:
            out = self.reload(visible_layers, parameters, context, feedback)
            print(out)
            return out

        return {"error": "No visible layers available", "success": False}

    def postProcessAlgorithm(self, context, feedback):
        root = context.project().layerTreeRoot()
        for child in root.children():
            if child.isVisible() and not isinstance(child, QgsLayerTreeLayer):
                print(f"group name = {child.name()}")
                LayerGroupPostProcessor.sort_group(child)
        return {}
