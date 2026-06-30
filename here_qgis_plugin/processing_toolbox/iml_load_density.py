###############################################################################
#
# Copyright (c) 2023 HERE Europe B.V.
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
    QgsProcessingParameterEnum,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFile,
    QgsProcessingParameterString,
)

from ..settings import get_catalog_hrn, get_path, get_project_hrn
from ..style_set import StyleConfig
from .file_type import FileType
from .here_processing_base import HereProcessingAlgorithm
from .iml_load_layer import LoadIMLayer
from .processing_utils import LayerPostProcessor


class LoadIMLayerDensity(HereProcessingAlgorithm):
    def __init__(self):
        super().__init__()
        # default IML to apply default styles

    @classmethod
    def createInstance(cls):
        return cls()

    def displayName(self) -> str:
        return "IML: Load Density IMLayer"

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
                "layer_id", "Specify layer id", multiLine=False, defaultValue="density"
            )
        )

        # extent
        self.addParameter(
            QgsProcessingParameterExtent(
                "extent",
                "Region of interest",
                defaultValue=None,
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

    def processAlgorithm(self, parameters, context, feedback):
        """
        HERE is where the processing itself takes place.
        """
        alg = LoadIMLayer.createInstance()
        parameters["iml_context"] = 0
        try:
            output = processing.run(
                alg,
                parameters,
                context=context,
                feedback=feedback,
            )
            return output
        except Exception as e:
            feedback.reportError(repr(e), False)
            return {"success": False, "error": repr(e)}

    def postProcessAlgorithm(
        self, context: QgsProcessingContext, feedback: QgsProcessingFeedback
    ) -> Dict[str, Any]:
        LayerPostProcessor.post_process(context, feedback)
        LayerPostProcessor.group_layers(context)
        return {}
