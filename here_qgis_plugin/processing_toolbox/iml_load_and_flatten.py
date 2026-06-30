###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from typing import Any, Dict

import processing
from qgis.core import (
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFile,
    QgsProcessingParameterString,
    QgsVectorLayer,
)
from typing_extensions import deprecated

from here_qgis.io.layer_storage import LayerStorage

from .. import config
from ..settings import get_catalog_hrn, get_path, get_project_hrn
from ..style_set import StyleConfig
from .file_type import FileType
from .get_and_load import GetAndLoad
from .here_processing_base import HereProcessingAlgorithm
from .iml_flatten_to_csv import IMLFlattenToCSV
from .processing_utils import LayerPostProcessor


@deprecated("class will be deleted in the future")
class IMLLoadAndFlatten(HereProcessingAlgorithm):
    @classmethod
    def createInstance(cls) -> "HereProcessingAlgorithm":
        return cls()

    def displayName(self) -> str:
        return "IML: Load and flatten data"

    def initAlgorithm(self, configuration=None):
        self.addParameter(
            QgsProcessingParameterFile(
                "HERE_CREDENTIALS_FILE",
                "Specify HERE credentials file",
                behavior=QgsProcessingParameterFile.Behavior.File,
                fileFilter="All Files (*.*)",
                defaultValue=get_path(),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                "project_hrn",
                "Specify Project HRN",
                multiLine=False,
                defaultValue=get_project_hrn(),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                "catalog_hrn",
                "Specify catalog:hrn",
                multiLine=False,
                defaultValue=get_catalog_hrn(),
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                "layer_id", "Specify layer id", multiLine=False, defaultValue="topology"
            )
        )

        self.addParameter(
            QgsProcessingParameterExtent(
                "extent", "Region of interest", defaultValue=None
            ),
            createOutput=True,
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

        # select output file type
        self.addParameter(
            QgsProcessingParameterEnum(
                "file_type",
                "Select file type",
                options=[file.name for file in FileType],
                allowMultiple=False,
                usesStaticStrings=True,
                defaultValue=FileType.GEOPACKAGE.name,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                "display_layer",
                "Flatten and original layer will be displayed on canvas",
                defaultValue=False,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                "flatten_only",
                "ONLY flatten layer will be displayed on canvas",
                defaultValue=False,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        bbox = self.get_bbox_from_params(parameters, "extent", context)
        get_and_load = GetAndLoad(bbox, parameters, feedback, context)

        layer_name, folder_name, layer_feature = get_and_load.get_features()
        imlsave_obj = LayerStorage(
            layer_name,
            folder_name,
            layer_feature,
            base_dir=config.USER_PLUGIN_DIR,
        )

        geojson_filename = imlsave_obj.features_to_geojson()
        pure_geojson_layer = QgsVectorLayer(geojson_filename, f"{layer_name}", "ogr")
        context.project().instance().addMapLayer(pure_geojson_layer)

        style_set_info = StyleConfig.to_info(
            pure_geojson_layer.id(),
            parameters["style_set"],  # , self.wkb_type_to_geom_type(geom_type)
        )
        style_set_info_str = StyleConfig.style_set_to_str(style_set_info)
        LayerPostProcessor.set_style(style_set_info_str, pure_geojson_layer)
        LayerPostProcessor.set_filetype(parameters["file_type"], pure_geojson_layer)

        iml_flatten_params = {
            "layer_id": pure_geojson_layer.id(),
            "display_layer": parameters["display_layer"] or parameters["flatten_only"],
        }

        iml_flatten_alg = IMLFlattenToCSV.createInstance()
        flatten_output = processing.runAndLoadResults(
            iml_flatten_alg,
            iml_flatten_params,
            context=context,
            feedback=feedback,
        )

        outputs = {}
        outputs["flatten"] = flatten_output
        if not parameters["flatten_only"]:
            outputs["load"] = get_and_load.load_to_qgis(
                imlsave_obj, parameters["file_type"]
            )

        context.project().instance().removeMapLayer(pure_geojson_layer.id())
        # os.remove(geojson_filename)
        outputs["success"] = True
        return outputs

    def postProcessAlgorithm(
        self, context: QgsProcessingContext, feedback: QgsProcessingFeedback
    ) -> Dict[str, Any]:
        LayerPostProcessor.post_process(context, feedback)
        return {}
