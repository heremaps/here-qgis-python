# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from typing import Any, Dict, Final, NamedTuple, Tuple

import processing
from qgis.core import (
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingMultiStepFeedback,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFile,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)
from qgis.utils import iface

from ..settings import get_path, get_project_hrn, get_vml_catalog_hrn
from ..style_set import StyleConfig
from .here_processing_base import HereProcessingAlgorithm
from .processing_utils import LayerGroupPostProcessor
from .vml_layer import LoadVersionedLayer


class BatchLoadVersionedLayer(HereProcessingAlgorithm):
    LAYER_IDS = [
        "address",
        "place",
        "relation",
        "topology",
        "roadtopology",
        "building",
        "carto",
        "admin",
    ]

    class Params(NamedTuple):
        CATALOG_HRN: Any
        EXTENT: Any
        LAYER_ENUMS: Any
        HERE_CREDENTIALS_FILE: Any
        STYLE_SET: Any
        PROJECT_HRN: Any
        IS_FLATTEN: Any
        LEVEL: Any
        PARTITION_IDS: Any
        CATALOG_VERSION: Any

    class Output(NamedTuple):
        OUTPUT: Any

    PARAMS: Final[Params] = Params(**{k: k for k in Params._fields})
    OUTPUT: Final[Output] = Output(**{k: k for k in Output._fields})

    @classmethod
    def createInstance(cls):
        return cls()

    def displayName(self) -> str:
        return "VML: Load Versioned Catalog"

    def initAlgorithm(self, config=None):
        # Specify HERE credentials file
        self.addParameter(
            QgsProcessingParameterFile(
                self.PARAMS.HERE_CREDENTIALS_FILE,
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
                self.PARAMS.PROJECT_HRN,
                "Specify project hrn",
                multiLine=False,
                defaultValue=get_project_hrn(),
                optional=True,
            )
        )

        # Specify catalog:hrn
        self.addParameter(
            QgsProcessingParameterString(
                self.PARAMS.CATALOG_HRN,
                "Specify catalog hrn",
                multiLine=False,
                defaultValue=get_vml_catalog_hrn(),
            )
        )

        # version
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PARAMS.CATALOG_VERSION,
                "Specify catalog version, use latest if not set",
                defaultValue=None,
                optional=True,
                minValue=0,
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.PARAMS.LAYER_ENUMS,
                "Select layers",
                options=self.LAYER_IDS,
                allowMultiple=True,
                usesStaticStrings=True,
                defaultValue=self.LAYER_IDS,
            )
        )

        # Region of interest
        self.addParameter(
            QgsProcessingParameterExtent(
                self.PARAMS.EXTENT,
                "Region of interest",
                defaultValue=None,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.PARAMS.PARTITION_IDS,
                "Partition Ids (comma-separated list)",
                defaultValue="",
                optional=True,
            )
        )

        # zoom level
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PARAMS.LEVEL,
                "Zoom level",
                defaultValue=None,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.PARAMS.STYLE_SET,
                "Select style set",
                options=StyleConfig.STYLE_GROUPS,
                allowMultiple=False,
                usesStaticStrings=False,
                defaultValue=StyleConfig.NO_STYLE_IDX,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.PARAMS.IS_FLATTEN,
                "Flatten nested JSON string (GDAL >= 3.8",
                defaultValue=False,
            )
        )

        # self.addOutput(
        #     QgsProcessingOutputMultipleLayers(self.OUTPUT.OUTPUT, "Vector layers")
        # )

    def checkParameterValues(
        self, parameters: Dict[str, Any], context: QgsProcessingContext
    ) -> Tuple[bool, str]:
        return LoadVersionedLayer.checkParameterValues(self, parameters, context)

    def processAlgorithm(self, parameters, context, model_feedback):
        VALUES = self.Params(
            CATALOG_HRN=self.parameterAsString(
                parameters, self.PARAMS.CATALOG_HRN, context
            ),
            LAYER_ENUMS=[
                self.LAYER_IDS[layer] if isinstance(layer, int) else layer
                for layer in parameters[self.PARAMS.LAYER_ENUMS]
            ],
            HERE_CREDENTIALS_FILE=self.parameterAsFile(
                parameters, self.PARAMS.HERE_CREDENTIALS_FILE, context
            ),
            STYLE_SET=self.parameterAsInt(parameters, self.PARAMS.STYLE_SET, context),
            PROJECT_HRN=self.parameterAsString(
                parameters, self.PARAMS.PROJECT_HRN, context
            ),
            IS_FLATTEN=self.parameterAsBoolean(
                parameters, self.PARAMS.IS_FLATTEN, context
            ),
            LEVEL=parameters[self.PARAMS.LEVEL],
            CATALOG_VERSION=parameters.get(self.PARAMS.CATALOG_VERSION, None),
            PARTITION_IDS=parameters.get(self.PARAMS.PARTITION_IDS, ""),
            EXTENT=parameters.get(self.PARAMS.EXTENT, None),
        )

        self.VALUES = VALUES

        feedback = QgsProcessingMultiStepFeedback(
            len(VALUES.LAYER_ENUMS), model_feedback
        )
        outputs = {}
        self.alg_store = dict()

        step_count = len(VALUES.LAYER_ENUMS)
        for i, layer_id in enumerate(VALUES.LAYER_ENUMS):
            feedback.setCurrentStep(i)
            feedback.pushInfo("step %s %s" % (i, layer_id))
            if feedback.isCanceled():
                return {"success": False}

            alg_params = LoadVersionedLayer.Params(
                HERE_CREDENTIALS_FILE=VALUES.HERE_CREDENTIALS_FILE,
                CATALOG_HRN=VALUES.CATALOG_HRN,
                PROJECT_HRN=VALUES.PROJECT_HRN,
                EXTENT=VALUES.EXTENT,
                STYLE_SET=VALUES.STYLE_SET,
                IS_FLATTEN=VALUES.IS_FLATTEN,
                LAYER_ID=layer_id,
                PARTITION_IDS=VALUES.PARTITION_IDS,
                LEVEL=VALUES.LEVEL,
                CATALOG_VERSION=VALUES.CATALOG_VERSION,
            )._asdict()
            feedback.pushInfo("step {}/{}: {}".format(i, step_count, alg_params))

            alg = LoadVersionedLayer.createInstance()
            # outputs[layer_id] = processing.runAndLoadResults(
            #     alg, alg_params, context=context, feedback=feedback
            # )
            try:
                outputs[layer_id] = {"success": False}
                outputs[layer_id] = processing.run(
                    alg,
                    alg_params,
                    context=context,
                    feedback=feedback,
                    is_child_algorithm=True,
                )
                # self.alg_store[layer_id] = alg
            except Exception as e:
                feedback.reportError(repr(e), False)

        feedback.setCurrentStep(i + 1)
        outputs["success"] = True
        return outputs

    def postProcessAlgorithm(
        self, context: QgsProcessingContext, feedback: QgsProcessingFeedback
    ) -> Dict[str, Any]:
        # return {}
        if iface is not None:
            iface.layerTreeView().setUpdatesEnabled(False)
        try:
            group_name = self.VALUES.CATALOG_HRN.split(":")[-1]
            # group of layers
            group = LayerGroupPostProcessor.create_layer_group(group_name, context)
            LayerGroupPostProcessor.insert_group_to_root(context, group)

            # # group layer
            # glayer = LayerGroupPostProcessor.create_glayer(group_name, context)
            # LayerGroupPostProcessor.insert_glayer_to_root(context, glayer)

        finally:
            if iface is not None:
                iface.layerTreeView().setUpdatesEnabled(True)
        return {}
