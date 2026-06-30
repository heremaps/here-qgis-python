###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterVectorLayer,
    QgsVectorLayer,
)
from typing_extensions import deprecated

from here_qgis.flatten.flatten import Flatten
from here_qgis.helper_functions import (
    WHOLE_LAYER,
    extract_filename,
    get_filename_without_ext,
)

from .here_processing_base import HereProcessingAlgorithm
from .layer_metadata import LayerMetadata


@deprecated("class will be deleted in the future")
class IMLFlattenToCSV(HereProcessingAlgorithm):
    """Class flatten the GeoJSON: dict -> geopandas -> save to .csv"""

    @classmethod
    def createInstance(cls) -> "HereProcessingAlgorithm":
        return cls()

    def displayName(self) -> str:
        return "IML: Flatten"

    def initAlgorithm(self, configuration=None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "layer_id",
                "Select layer for flatten",
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                "display_layer",
                "If checked, layer will be displayed on canvas",
                defaultValue=False,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        layer_id = parameters["layer_id"]
        selected_layer: QgsVectorLayer = context.getMapLayer(layer_id)
        filename = selected_layer.dataProvider().dataSourceUri()
        filetype = LayerMetadata.get_filetype(selected_layer)

        GEOJSON = "geojson"
        GEOPACKAGE = "gpkg"

        if filetype == "GEOJSON":
            name_without_ext = get_filename_without_ext(filename, GEOJSON)
        elif filetype == "GEOPACKAGE":
            name_without_ext = get_filename_without_ext(filename, GEOPACKAGE)
            filename = extract_filename(filename)
        else:
            err = "Missing metadata. Source layer must be .geojson or .gpkg file"
            feedback.reportError(err)
            return {"success": False, "error": err}

        types_filename = name_without_ext + "_flattened_types.json"
        filename_csv = name_without_ext + "_flattened.csv"
        try:
            flatten_obj = Flatten(filename, types_filename, filename_csv)
        except Exception as e:
            feedback.pushInfo(f"{e}")
            return {"success": False, "error": repr(e)}

        flatten_obj.process_flatten()

        if parameters["display_layer"]:
            uri = f"file:///{filename_csv}?wktField=geometry"
            vlayer = QgsVectorLayer(
                uri, selected_layer.name() + " flattened", "delimitedtext"
            )
            vlayer.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        else:
            vlayer = QgsVectorLayer(
                filename_csv, selected_layer.name() + " flattened", "ogr"
            )

        LayerMetadata.copy_metadata(selected_layer, vlayer)
        LayerMetadata.add_loader_props(vlayer, flattened=WHOLE_LAYER)

        output = {}

        context.project().instance().addMapLayer(vlayer)

        output["message"] = f"Layer {selected_layer.name()} flattened!"
        output["success"] = True
        return output
