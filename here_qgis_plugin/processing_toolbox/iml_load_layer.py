###############################################################################
#
# Copyright (c) 2023 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from typing import Any, Dict

from qgis.core import (
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingParameterEnum,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFile,
    QgsProcessingParameterString,
)

from here_qgis.io.layer_storage import LayerStorage

from .. import config
from ..settings import get_catalog_hrn, get_path, get_project_hrn
from ..style_set import StyleConfig
from .file_type import FileType
from .get_and_load import GetAndLoad
from .here_processing_base import HereProcessingAlgorithm
from .processing_utils import IML_CONTEXT, LayerPostProcessor


class LoadIMLayer(HereProcessingAlgorithm):
    @classmethod
    def createInstance(cls):
        return cls()

    def displayName(self) -> str:
        return "IML: Load IML Layer"

    def __init__(self):
        super().__init__()

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """
        # HERE credentials
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

        # project hrn
        self.addParameter(
            QgsProcessingParameterString(
                "project_hrn",
                "Specify Project HRN",
                multiLine=False,
                defaultValue=get_project_hrn(),
                optional=True,
            )
        )

        # catalog hrn
        self.addParameter(
            QgsProcessingParameterString(
                "catalog_hrn",
                "Specify catalog:hrn",
                multiLine=False,
                defaultValue=get_catalog_hrn(),
            )
        )

        # layer id
        self.addParameter(
            QgsProcessingParameterString(
                "layer_id", "Specify layer id", multiLine=False, defaultValue="topology"
            )
        )

        # extent
        self.addParameter(
            QgsProcessingParameterExtent(
                "extent", "Region of interest", defaultValue=None
            ),
            createOutput=True,
        )

        # style set
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
            QgsProcessingParameterEnum(
                "iml_context",
                "Mode for composite layer",
                options=list(map(lambda m: m[0], IML_CONTEXT)),
                optional=True,
                defaultValue=IML_CONTEXT[0][0],
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                "query",
                "Query for specific IML data",
                optional=True,
                defaultValue="",
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        HERE is where the processing itself takes place.
        """

        bbox = self.get_bbox_from_params(parameters, "extent", context)
        composite = IML_CONTEXT[parameters["iml_context"]][1]

        output = {}
        for comp_context in composite:
            get_and_load = GetAndLoad(
                bbox,
                parameters,
                feedback,
                context,
                comp_context,
                parameters.get("query", ""),
            )

            layer_name, folder_name, layer_feature = get_and_load.get_features()

            imlsave_obj = LayerStorage(
                layer_name, folder_name, layer_feature, base_dir=config.TMP_DIR
            )

            if len(layer_feature["features"]) > 0:
                # the same output structure
                load_out = get_and_load.load_to_qgis(
                    imlsave_obj,
                    parameters["file_type"],
                    parameters["layer_id"] == "density",
                )
                if load_out:
                    output[comp_context] = load_out

        if len(output.keys()) > 0:
            output["success"] = True
            return output

        feedback.reportError(
            f"No features loaded from {parameters['layer_id']} layer,"
            + f"extent {parameters['extent']}"
        )

        return {
            "success": False,
            "error": (
                f"No features loaded from {parameters['layer_id']} layer, "
                + f"extent {parameters['extent']}"
            ),
        }

    def postProcessAlgorithm(
        self, context: QgsProcessingContext, feedback: QgsProcessingFeedback
    ) -> Dict[str, Any]:
        LayerPostProcessor.post_process(context, feedback)
        return {}
