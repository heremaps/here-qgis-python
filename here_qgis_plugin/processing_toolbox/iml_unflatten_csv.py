###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from typing import Any, Dict

from qgis.core import (
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingParameterMapLayer,
    QgsVectorLayer,
)
from typing_extensions import deprecated

from here_qgis.flatten.unflatten import Unflatten
from here_qgis.helper_functions import (
    WHOLE_LAYER,
    extract_filename,
    get_filename_without_ext,
)

from .here_processing_base import HereProcessingAlgorithm
from .prepare_unflatten_processing import (
    prepare_unflatten_processing,
    process_unflatten_processing,
)
from .processing_utils import LayerPostProcessor


@deprecated("class will be deleted in the future")
class IMLUnflattenCSV(HereProcessingAlgorithm):
    """Class unflattens the csv file: csv -> geopandas -> dict -> GeoJSON"""

    @classmethod
    def createInstance(cls) -> "HereProcessingAlgorithm":
        return cls()

    def displayName(self) -> str:
        return "IML: Unflatten table"

    def initAlgorithm(self, configuration=None):
        self.addParameter(
            QgsProcessingParameterMapLayer(
                "layer_id",
                "Select layer to unflatten",
            )
        )

    def unflatten_whole_layer(self, selected_layer: QgsVectorLayer, feedback):
        filename = selected_layer.dataProvider().dataSourceUri()
        filename = extract_filename(filename)

        CSV = "csv"
        filename_without_ext = get_filename_without_ext(filename, CSV)

        if filename_without_ext == "":
            feedback.reportError(
                "Wrong layer selected. Source of layer must be a .csv file"
            )
            return None, "", "Wrong layer selected. Source of layer must be a .csv file"

        new_filename = filename_without_ext + "_unflattened.geojson"
        types_filename = filename_without_ext + "_types.json"
        try:
            unflatten_obj = Unflatten(
                filename=filename,
                types_filename=types_filename,
                new_filename=new_filename,
            )
        except (IOError, ValueError) as e:
            feedback.reportError(f"Error: {e}")
            return None, "", repr(e)

        return unflatten_obj, new_filename, ""

    def processAlgorithm(self, parameters, context, feedback):
        selected_layer, flattened_name, how_flattened = prepare_unflatten_processing(
            parameters, context
        )
        if how_flattened == WHOLE_LAYER:
            unflatten_obj, new_filename, error = self.unflatten_whole_layer(
                selected_layer, feedback
            )
            if error != "":
                return {"error": error, "success": False}
        else:
            feedback.reportError(
                "Cannot unflatten this layer. Use 'IML: Unflatten on the fly'"
            )
            return {
                "error": "Cannot unflatten this layer. Use 'IML: Unflatten on the fly'",
                "success": False,
            }

        return process_unflatten_processing(
            unflatten_obj,
            new_filename,
            selected_layer,
            flattened_name,
            False,
            context,
            feedback,
        )

    def postProcessAlgorithm(
        self, context: QgsProcessingContext, feedback: QgsProcessingFeedback
    ) -> Dict[str, Any]:
        LayerPostProcessor.post_process(context, feedback)
        return {}
