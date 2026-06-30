# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.core import (
    QgsProcessingParameterEnum,
    QgsProcessingParameterVectorLayer,
    QgsVectorLayer,
)

from ..style_set import StyleConfig
from .here_processing_base import HereProcessingAlgorithm
from .layer_metadata import LayerMetadataPluginV1
from .processing_utils import LayerPostProcessor, get_geom_type_str


class ApplyStyleToIML(HereProcessingAlgorithm):
    @classmethod
    def createInstance(cls) -> "HereProcessingAlgorithm":
        return cls()

    def displayName(self) -> str:
        return "MOM: Styling single layer"

    def initAlgorithm(self, configuration=None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "layer_id",
                "Specify to which layer new style should be applied",
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

        self.addParameter(
            QgsProcessingParameterEnum(
                "layer_feature_type",
                "Select layer feature type",
                options=StyleConfig.LAYER_IDS,
                usesStaticStrings=True,
                allowMultiple=False,
                optional=True,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        HERE is where the processing itself takes place.
        """
        layer: QgsVectorLayer = context.project().mapLayer(parameters["layer_id"])
        style_set_idx = parameters["style_set"]
        layer_feature_type = (
            LayerPostProcessor.detect_feature_type(layer)
            or LayerMetadataPluginV1.detect_feature_type(layer)
            or parameters.get("layer_feature_type")
        )

        style_set_info = StyleConfig.to_info(
            layer_feature_type, style_set_idx, geom_type=get_geom_type_str(layer)
        )

        if not StyleConfig.is_valid_style(style_set_info):
            message = "Style '{}' ({}, {}) is not available for layer '{}'".format(
                style_set_info["style_set_name"],
                style_set_info["layer_id"],
                style_set_info["geom_type"],
                layer.name(),
            )
            self.warn(
                feedback,
                message,
            )
            return {"error": message, "success": False}

        style_set_info_str = StyleConfig.style_set_to_str(style_set_info)
        LayerPostProcessor.set_style(style_set_info_str, layer)
        if not LayerPostProcessor.update_style(layer):
            message = "Style '{}' ({}, {}) failed to load for layer '{}'".format(
                style_set_info["style_set_name"],
                style_set_info["layer_id"],
                style_set_info["geom_type"],
                layer.name(),
            )
            self.warn(
                feedback,
                message,
            )
            return {"error": message, "success": False}

        layer.triggerRepaint()
        return {"layer_id": layer.id(), "success": True}
