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
    QgsProcessingMultiStepFeedback,
    QgsProcessingParameterEnum,
    QgsVectorLayer,
)
from qgis.utils import iface

from ..style_set import StyleConfig
from . import ApplyStyleToIML
from .here_processing_base import HereProcessingAlgorithm
from .layer_metadata import LayerMetadata


class OneClickStyleIML(HereProcessingAlgorithm):
    @classmethod
    def createInstance(cls) -> "HereProcessingAlgorithm":
        return cls()

    def displayName(self) -> str:
        return "MOM: Quick styling"

    def initAlgorithm(self, configuration=None):
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

    def checkParameterValues(self, parameters, context):
        status, msg = super().checkParameterValues(parameters, context)
        if not status:
            return status, msg

        if iface:
            selected_layers = iface.layerTreeView().selectedLayersRecursive()
            selected_vector_layers = [
                layer for layer in selected_layers if isinstance(layer, QgsVectorLayer)
            ]
            if not selected_vector_layers:
                status, msg = False, "no vector layer selected"
        return status, msg

    def processAlgorithm(self, parameters, context, feedback):
        style_set_idx = parameters["style_set"]

        outputs = {}
        updated_layers_count = 0
        selected_layers_count = 0

        if iface:
            selected_layers = iface.layerTreeView().selectedLayersRecursive()
            selected_layers_count = len(selected_layers)

            step_feedback = QgsProcessingMultiStepFeedback(
                selected_layers_count, feedback
            )
            step_feedback.setCurrentStep(0)

            alg = ApplyStyleToIML.createInstance()
            for i, vlayer in enumerate(selected_layers):
                layer_id = vlayer.id()
                output_key = LayerMetadata.get_layer_id(vlayer)
                params = {
                    "layer_id": layer_id,
                    "style_set": style_set_idx,
                    "layer_feature_type": None,
                }
                try:
                    output = processing.run(
                        alg,
                        params,
                        context=context,
                        feedback=feedback,
                        is_child_algorithm=True,
                    )
                    outputs[output_key] = output
                except Exception as e:
                    feedback.reportError(repr(e), False)
                    outputs[output_key] = None

                step_feedback.setCurrentStep(i + 1)

            updated_layers_count = len(
                list(output for output in outputs.values() if output)
            )

            feedback.pushInfo(
                f"{updated_layers_count}/{selected_layers_count} layers updated with"
                f" style '{StyleConfig.STYLE_GROUPS[style_set_idx]}'"
            )

        return {
            "output": outputs,
            "updated_layers_count": updated_layers_count,
            "selected_layers_count": selected_layers_count,
            "success": True,
        }
