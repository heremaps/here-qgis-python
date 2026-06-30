# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import processing
from qgis.core import (
    QgsProcessing,
    QgsProcessingMultiStepFeedback,
    QgsProcessingParameterEnum,
    QgsProcessingParameterMultipleLayers,
    QgsProcessingParameterString,
)

from ..style_set import StyleConfig
from .here_processing_base import HereProcessingAlgorithm
from .iml_apply_style import ApplyStyleToIML


class ApplyStyleToManyIMLs(HereProcessingAlgorithm):
    @classmethod
    def createInstance(cls) -> "HereProcessingAlgorithm":
        return cls()

    def displayName(self) -> str:
        return "MOM: Styling multiple layer"

    def initAlgorithm(self, configuration=None):
        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                "layers_ids",
                "Specify to which layers new style should be applied",
                layerType=QgsProcessing.SourceType.TypeVectorAnyGeometry,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                "layers_feature_types",
                (
                    "Specify in correct order what feature type layers have (comma"
                    " separated)"
                ),
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
        layer_ids = parameters["layers_ids"]
        style_set_idx = parameters["style_set"]
        feature_types = [
            s.strip() for s in parameters["layers_feature_types"].split(",")
        ]

        outputs = {}
        updated_layers_count = 0
        selected_layers_count = len(layer_ids)

        step_feedback = QgsProcessingMultiStepFeedback(selected_layers_count, feedback)
        step_feedback.setCurrentStep(0)

        alg = ApplyStyleToIML.createInstance()
        for i, layer_id in enumerate(layer_ids):
            feature_type = feature_types[i] if i < len(feature_types) else None
            params = {
                "layer_id": layer_id,
                "style_set": style_set_idx,
                "layer_feature_type": feature_type,
            }
            try:
                output = processing.run(
                    alg,
                    params,
                    context=context,
                    feedback=feedback,
                    is_child_algorithm=True,
                )
                outputs[feature_type] = output
            except Exception as e:
                feedback.reportError(repr(e), False)
                outputs[feature_type] = None

            step_feedback.setCurrentStep(i + 1)

        updated_layers_count = len(
            list(output for output in outputs.values() if output)
        )

        message = (
            f"{updated_layers_count}/{selected_layers_count} layers updated with"
            f" style '{StyleConfig.STYLE_GROUPS[style_set_idx]}'"
        )

        step_feedback.pushInfo(message)

        return {
            "output": outputs,
            "updated_layers_count": updated_layers_count,
            "selected_layers_count": selected_layers_count,
            "success": True,
            "message": message,
        }
