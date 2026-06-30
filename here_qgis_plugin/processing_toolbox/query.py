# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from typing import Any, Dict, List

import processing
from qgis.core import (
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorLayer,
)

from .here_processing_base import HereProcessingAlgorithm


class QueryAllAttributes(HereProcessingAlgorithm):
    EXPRESSION_TEMPLATE = "try(to_json(attributes()) like '%{}%', 0)"

    @classmethod
    def createInstance(cls):
        return cls()

    def displayName(self):
        return "Util: Query all attributes from layer"

    def tags(self) -> List[str]:
        return "query,select,json".split(",")

    def initAlgorithm(self, configuration: Dict[str, Any] = None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "input_layer",
                "Input layer",
                defaultValue="",
                optional=False,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                "query_string",
                "Query string",
                multiLine=False,
                defaultValue="22108999",
                optional=False,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                "is_extract",
                "Extract results to temporary layer",
                defaultValue=False,
                optional=False,
            )
        )

    def processAlgorithm(
        self,
        parameters: Dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> Dict[str, Any]:
        print(parameters)

        output = dict()
        # QgsProcessingUtils.mapLayerFromString()
        vlayer = self.parameterAsVectorLayer(parameters, "input_layer", context)
        print(vlayer.id())
        output["selectbyexpression"] = processing.run(
            "qgis:selectbyexpression",
            {
                "INPUT": parameters["input_layer"],
                "EXPRESSION": self.EXPRESSION_TEMPLATE.format(
                    parameters["query_string"]
                ),
                "METHOD": 0,
            },
            feedback=feedback,
            context=context,
            is_child_algorithm=True,
        )

        if parameters["is_extract"]:
            output["saveselectedfeatures"] = processing.runAndLoadResults(
                "native:saveselectedfeatures",
                {"INPUT": parameters["input_layer"], "OUTPUT": "TEMPORARY_OUTPUT"},
                feedback=feedback,
                context=context,
            )

        return output

    def postProcessAlgorithm(
        self, context: QgsProcessingContext, feedback: QgsProcessingFeedback
    ) -> Dict[str, Any]:
        print(context.layersToLoadOnCompletion())
        return {}
