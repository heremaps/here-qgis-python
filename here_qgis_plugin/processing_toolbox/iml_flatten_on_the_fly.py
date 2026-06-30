###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import json

from qgis.core import QgsProcessingParameterVectorLayer, QgsVectorLayer

from here_qgis.helper_functions import ON_THE_FLY

from ..flatten.flatten_qgs import FlattenQgs
from .here_processing_base import HereProcessingAlgorithm
from .layer_metadata import LayerMetadata


class FlattenOnFly(HereProcessingAlgorithm):
    """Class flattens the data. Currently it is intended to be
    used with existing QgsVectorLayer.

    List[QgsFeatures] -> flattens to dict -> List[QgsFeatures] -> memory layer
    """

    @classmethod
    def createInstance(cls):
        return cls()

    def displayName(self) -> str:
        return "IML: Flatten on the fly"

    def initAlgorithm(self, configuration=None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "layer",
                "Select layer",
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        layer: QgsVectorLayer = context.project().mapLayer(parameters["layer"])
        selected_features = layer.selectedFeatures()
        # if len(selected_features) == 0:
        #     err = "No features selected!"
        #     feedback.pushWarning(err)
        #     return {"success": False, "error": err}
        if not selected_features:
            feedback.pushInfo(
                f"No features selected in '{layer.name()}'. Flattening all features."
            )
            selected_features = list(layer.getFeatures())

        flat_obj = FlattenQgs(features=selected_features)
        features, fields = flat_obj.flatten_on_the_fly()

        geom_type = json.loads(selected_features[0].geometry().asJson())["type"]
        vlayer = QgsVectorLayer(
            f"{geom_type}?crs=EPSG:4326",
            layer.name() + " flattened temporary",
            "memory",
        )

        provider = vlayer.dataProvider()

        provider.addAttributes(fields)
        vlayer.updateFields()

        # layer feature ids not persist after provider.addFeatures
        _ok, _features = provider.addFeatures(features)
        vlayer.updateExtents()

        LayerMetadata.copy_metadata(layer, vlayer)
        LayerMetadata.add_loader_props(vlayer, flattened=ON_THE_FLY)

        output = {}
        context.project().instance().addMapLayer(vlayer)

        output["message"] = (
            f"Selected features from {layer.name()} flattened to temporary layer"
        )
        output["new_layer_id"] = vlayer.id()
        output["success"] = True
        return output
