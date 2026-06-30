# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import json
from typing import Any, Dict, List, Optional, Tuple

import processing
from qgis.core import (
    QgsFeatureRequest,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorLayer,
)

from . import LoadVersionedLayer, QueryAllAttributes
from .here_processing_base import HereProcessingAlgorithm


class LoadQueryVersionedLayer(HereProcessingAlgorithm):
    OUTPUT = "output"

    @classmethod
    def createInstance(cls):
        return cls()

    def displayName(self):
        return "VML: Load and Query"

    def initAlgorithm(self, configuration: Dict[str, Any] = None):
        LoadVersionedLayer.initAlgorithm(self, configuration)

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "reference_layer",
                "Reference layer, contains selected partition ids as input",
                # [QgsProcessing.SourceType.TypeVectorPolygon],
                defaultValue=None,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                "query_string",
                "Query string",
                multiLine=False,
                defaultValue="",
                optional=True,
            )
        )

    def checkParameterValues(
        self, parameters: Dict[str, Any], context: QgsProcessingContext
    ) -> Tuple[bool, str]:
        ok, msg = super(HereProcessingAlgorithm, self).checkParameterValues(
            parameters, context
        )
        if not ok:
            return ok, msg
        ok_spatial = bool(
            parameters.get(LoadVersionedLayer.PARAMS.EXTENT)
            or parameters.get(LoadVersionedLayer.PARAMS.PARTITION_IDS)
            or self.get_selection_from_reference_layer(parameters, context) is not None
        )

        msg_spatial = (
            "Either extent, partition ids or valid reference layer parameter must be"
            " provided"
            if not ok_spatial
            else ""
        )
        print("checkParameterValues", ok_spatial)
        return ok_spatial, msg_spatial

    def get_selection_from_reference_layer(
        self, parameters: Dict, context
    ) -> Optional[List]:
        layer = self.parameterAsVectorLayer(parameters, "reference_layer", context)
        if layer and layer.isValid():
            selected_fids = layer.selectedFeatureIds()
            return selected_fids
        return None

    def processAlgorithm(
        self,
        parameters: Dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> Dict[str, Any]:
        output = dict()
        params = parameters

        layer = self.parameterAsVectorLayer(parameters, "reference_layer", context)
        if layer and layer.isValid():
            selected_fids = layer.selectedFeatureIds()
            feature_request = (
                QgsFeatureRequest(selected_fids)
                if selected_fids
                else QgsFeatureRequest()
            )
            lst_partition_ids = [
                str(feat.attribute("id")) for feat in layer.getFeatures(feature_request)
            ]
            partition_ids = ",".join(lst_partition_ids)

            feedback.pushInfo("Partition ids from reference layer:")
            feedback.pushCommandInfo(partition_ids)
            params = dict(parameters, PARTITION_IDS=partition_ids)

        feedback.pushInfo("processed input params:")
        feedback.pushCommandInfo(json.dumps({k: str(v) for k, v in params.items()}))

        output["load"] = processing.run(
            LoadVersionedLayer.createInstance(),
            params,
            feedback=feedback,
            context=context,
            is_child_algorithm=True,
        )

        if not output["load"]:
            msg = "loading failed"
            feedback.reportError(msg)
            output["success"] = False
            output["message"] = msg
            return output

        query_string = parameters["query_string"]

        if not query_string:
            output["success"] = False
            return output

        layer_id = output["load"]["layer_id"]
        output["query"] = processing.run(
            QueryAllAttributes.createInstance(),
            {
                "input_layer": layer_id,
                "query_string": parameters["query_string"],
                "is_extract": False,
            },
            feedback=feedback,
            context=context,
            is_child_algorithm=True,
        )

        output["success"] = True
        return output

    def postProcessAlgorithm(
        self, context: QgsProcessingContext, feedback: QgsProcessingFeedback
    ) -> Dict[str, Any]:
        print(context.layersToLoadOnCompletion())
        return {}
