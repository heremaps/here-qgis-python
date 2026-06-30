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
    QgsProcessingMultiStepFeedback,
    QgsProcessingParameterEnum,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFile,
    QgsProcessingParameterString,
)
from qgis.utils import iface

from ..settings import get_catalog_hrn, get_path, get_project_hrn
from ..style_set import StyleConfig
from .file_type import FileType
from .here_processing_base import HereProcessingAlgorithm, HereProcessingEnum
from .iml_load_layer import LoadIMLayer
from .processing_utils import IML_CONTEXT, LayerGroupPostProcessor


# TODO: save to one geopackage
class IMLBatchLoad(HereProcessingAlgorithm):
    """Loads all defautl layers in once with the same input parameters"""

    @classmethod
    def createInstance(cls) -> "HereProcessingAlgorithm":
        return cls()

    def displayName(self) -> str:
        return "IML: Load IML BaseMap"

    def __init__(self):
        super().__init__()
        self.context = QgsProcessingContext()
        self.feedback = QgsProcessingFeedback()

        self.layer_order = {
            "address": 0,
            "admin": 6,
            "building": 5,
            "carto": 4,
            "place": 1,
            "relation": 2,
            "topology": 3,
        }
        self.iml_layers = [
            "address",
            "admin",
            "building",
            "carto",
            "place",
            "relation",
            "topology",
        ]
        self.iml_layers_values = [
            index for index, predicatestring in enumerate(self.iml_layers)
        ]

    def initAlgorithm(self, config=None):
        # Specify HERE credentials file
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

        # Specify catalog:hrn
        self.addParameter(
            QgsProcessingParameterString(
                "catalog_hrn",
                "Specify catalog:hrn",
                multiLine=False,
                defaultValue=get_catalog_hrn(),
            )
        )
        self.addParameter(
            HereProcessingEnum(
                "iml_layers",
                "Select layers",
                options=self.iml_layers,
                allowMultiple=True,
                defaultValue=self.iml_layers_values,
            )
        )

        # Region of interest
        self.addParameter(
            QgsProcessingParameterExtent(
                "extent", "Region of interest", defaultValue=None
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

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress
        # reports are adjusted for the overall progress through the model

        layers = []
        for layer_value in parameters["iml_layers"]:
            if isinstance(layer_value, int):
                layers.append(self.iml_layers[layer_value])
            elif isinstance(layer_value, str):
                layers.append(layer_value)

        feedback = QgsProcessingMultiStepFeedback(len(layers), model_feedback)

        outputs = {}
        self.alg_store = dict()

        iml_context = parameters["iml_context"] if "iml_context" in parameters else 0
        layer_params = {
            layer: {
                "HERE_CREDENTIALS_FILE": parameters.get("HERE_CREDENTIALS_FILE", ""),
                "project_hrn": parameters["project_hrn"],
                "catalog_hrn": parameters["catalog_hrn"],
                "extent": parameters["extent"],
                "file_type": parameters["file_type"],
                "layer_id": layer,
                "style_set": parameters["style_set"],
                "iml_context": iml_context,
                "query": parameters.get("query", ""),
            }
            for layer in layers
        }

        splitted_hrn = parameters["catalog_hrn"].split(":")
        group_name = splitted_hrn[-2] + ":" + splitted_hrn[-1]
        self.group_name = group_name

        step_count = len(layers)
        for i, layer_id in enumerate(layers):
            feedback.setCurrentStep(i)
            if feedback.isCanceled():
                return {"success": False}
            params = layer_params[layer_id]
            feedback.pushInfo("step {}/{}: {}".format(i, step_count, params))

            alg = LoadIMLayer.createInstance()
            try:
                outputs[layer_id] = {"success": False}
                outputs[layer_id] = processing.run(
                    alg,
                    layer_params[layer_id],
                    context=context,
                    feedback=feedback,
                    is_child_algorithm=True,
                )
                # self.alg_store[layer_id] = alg
            except Exception as e:
                outputs[layer_id]["error"] = repr(e)
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
            # group of layers
            group = LayerGroupPostProcessor.create_layer_group(self.group_name, context)
            LayerGroupPostProcessor.insert_group_to_root(context, group)

            # # group layer
            # glayer = LayerGroupPostProcessor.create_glayer(self.group_name, context)
            # LayerGroupPostProcessor.insert_glayer_to_root(context, glayer)
        finally:
            if iface is not None:
                iface.layerTreeView().setUpdatesEnabled(True)
        return {}
