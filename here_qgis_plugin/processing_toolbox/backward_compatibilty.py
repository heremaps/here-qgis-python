# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.core import QgsProcessingParameterVectorLayer, QgsVectorLayer

from .here_processing_base import HereProcessingAlgorithm
from .layer_metadata import BackwardCompatibilityMetadata


class BackwardCompatibilty(HereProcessingAlgorithm):
    @classmethod
    def createInstance(cls):
        return cls()

    def displayName(self) -> str:
        return "IML: Backward compatibility with V1 Plugin"

    def initAlgorithm(self, configuration=None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "qgis_layer_id",
                "Specify which layer should be reloaded",
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        vlayer: QgsVectorLayer = context.project().mapLayer(parameters["qgis_layer_id"])
        BackwardCompatibilityMetadata.make_compatible(vlayer)
        return {
            "success": True,
            "layer_id": vlayer.id(),
            "message": f"Layer {vlayer.name()} was made compatible with V1 Plugin",
        }
