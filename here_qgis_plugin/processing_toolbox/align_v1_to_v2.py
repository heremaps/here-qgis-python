###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import processing
from qgis.core import (
    QgsProcessingParameterEnum,
    QgsProcessingParameterVectorLayer,
    QgsVectorLayer,
)

from ..style_set import StyleConfig
from .here_processing_base import HereProcessingAlgorithm
from .iml_apply_style import ApplyStyleToIML
from .layer_metadata import LayerMetadataPluginV1


class AlignV1(HereProcessingAlgorithm):
    @classmethod
    def createInstance(cls):
        return cls()

    def displayName(self) -> str:
        return "Util: Align deprecated V1 layer"

    def initAlgorithm(self, configuration=None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "layer_id",
                "Specify which layer will be aligned",
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                "style_set",
                "Select style set",
                options=StyleConfig.STYLE_GROUPS,
                allowMultiple=False,
                usesStaticStrings=False,
                defaultValue=StyleConfig.DEFAULT_STYLE_IDX,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        vlayer: QgsVectorLayer = context.project().mapLayer(parameters["layer_id"])
        if not LayerMetadataPluginV1.is_V1_layer(vlayer):
            feedback.reportError("Selected layer is not HERE Plugin V1 layer!")
            return {"error": "Selected layer is not HERE Plugin V1 layer!"}
        LayerMetadataPluginV1.make_compatible_v2(vlayer)

        alg = ApplyStyleToIML.createInstance()
        apply_style_output = {}
        try:
            apply_style_output = processing.run(
                alg,
                parameters,
                context=context,
                feedback=feedback,
            )
        except Exception as e:
            feedback.reportError(repr(e), False)
        return apply_style_output
