###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os
import time
from typing import Any, Dict

from qgis.core import (
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterMapLayer,
    QgsVectorLayer,
)

from here_qgis.helper_functions import ON_THE_FLY

from .. import config
from ..flatten.unflatten_qgs import UnflattenQGS
from .here_processing_base import HereProcessingAlgorithm
from .prepare_unflatten_processing import (
    prepare_unflatten_processing,
    process_unflatten_processing,
)
from .processing_utils import LayerPostProcessor


class IMLUnflattenOnTheFly(HereProcessingAlgorithm):
    """Class unflattens layer that was flattened with on-the-fly.

    List[QgsFeatures] -> dict -> unflattens to dict -> List[dict] -> save to .geojson
    """

    @classmethod
    def createInstance(cls) -> "HereProcessingAlgorithm":
        return cls()

    def displayName(self) -> str:
        return "IML: Unflatten On The Fly"

    def initAlgorithm(self, configuration=None):
        self.addParameter(
            QgsProcessingParameterMapLayer(
                "layer_id",
                "Select layer to unflatten",
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                "unflatten_selected",
                "Unflatten selected features",
                defaultValue=False,
            )
        )

    def unflatten_on_the_fly(
        self,
        selected_layer: QgsVectorLayer,
        flattened_name: str,
        unflatten_selected: bool,
        feedback,
    ):
        new_filename = os.path.join(
            config.TMP_DIR,
            (
                flattened_name.lower().replace("-", "").replace(" ", "_")
                + "_unflattened_"
                + time.strftime("%Y%m%d-%H%M%S")
                + ".geojson"
            ),
        )
        if unflatten_selected:
            features = list(selected_layer.getSelectedFeatures())
        else:
            features = list(selected_layer.getFeatures())

        try:
            unflatten_obj = UnflattenQGS(qgis_features=features)

        except ValueError as e:
            feedback.reportError(f"Error: {e}")
            return None, "", repr(e)

        return unflatten_obj, new_filename, ""

    def processAlgorithm(self, parameters, context, feedback):
        selected_layer, flattened_name, how_flattened = prepare_unflatten_processing(
            parameters, context
        )
        if how_flattened == ON_THE_FLY:
            unflatten_obj, new_filename, error = self.unflatten_on_the_fly(
                selected_layer,
                flattened_name,
                parameters["unflatten_selected"],
                feedback,
            )
            if error != "":
                return {"error": error, "success": False}
        else:
            feedback.reportError(
                "Cannot unflatten this layer. Use 'IML: Unflatten table"
            )
            return {
                "error": "Cannot unflatten this layer. Use 'IML: Unflatten table",
                "success": False,
            }

        return process_unflatten_processing(
            unflatten_obj,
            new_filename,
            selected_layer,
            flattened_name,
            True,
            context,
            feedback,
        )

    def postProcessAlgorithm(
        self, context: QgsProcessingContext, feedback: QgsProcessingFeedback
    ) -> Dict[str, Any]:
        LayerPostProcessor.post_process(context, feedback)
        return {}
