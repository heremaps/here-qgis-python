###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from typing import Any, Dict

from qgis.core import QgsProcessingContext, QgsProcessingFeedback, QgsVectorLayer

from here_qgis.flatten.unflatten import Unflatten

from ..flatten.unflatten_qgs import UnflattenQGS
from .layer_metadata import LayerMetadata
from .processing_utils import LayerPostProcessor


def prepare_unflatten_processing(
    parameters: Dict[str, Any],
    context,
) -> tuple[QgsVectorLayer, str, str]:
    layer_id = parameters["layer_id"]
    selected_layer: QgsVectorLayer = context.getMapLayer(layer_id)
    flattened_name = selected_layer.name()
    how_flattened = LayerMetadata.get_loader_property(selected_layer, "flattened")
    if how_flattened is None:
        how_flattened = ""
    return selected_layer, flattened_name, how_flattened


def process_unflatten_processing(
    unflatten_obj: Unflatten,
    new_filename: str,
    selected_layer: QgsVectorLayer,
    flattened_name: str,
    on_the_fly: bool,
    context: QgsProcessingContext,
    feedback: QgsProcessingFeedback,
) -> dict:
    try:
        if isinstance(unflatten_obj, UnflattenQGS):
            unflatten_obj.unflatten_to_file(new_filename)
        else:
            unflatten_obj.process_unflatten()
    except IOError:
        feedback.reportError("Cannot create a .geojson file")
        return {"error": "Cannot create a .geojson file"}

    vlayer = QgsVectorLayer(new_filename, selected_layer.name() + " unflattened", "ogr")

    LayerMetadata.copy_metadata(selected_layer, vlayer)
    LayerPostProcessor.add_layer_into_context(context, vlayer)
    LayerPostProcessor.set_filetype("GEOJSON", vlayer)

    output = {}

    output["message"] = f"{flattened_name} unflattened"
    output["layer_id"] = vlayer.id()
    output["success"] = True
    return output
