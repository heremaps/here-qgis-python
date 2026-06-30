###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os

import processing
from qgis.core import (
    QgsProcessingMultiStepFeedback,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFile,
    QgsProject,
)
from qgis.utils import iface

from ..settings import get_path
from .here_processing_base import HereProcessingAlgorithm
from .iml_reload_layer import ReloadIMLayer
from .layer_metadata import LayerMetadata


class ReloadManyIMLLayers(HereProcessingAlgorithm):
    @classmethod
    def createInstance(cls):
        return cls()

    def displayName(self) -> str:
        return "IML: Reload Many Layers"

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
            QgsProcessingParameterExtent(
                "extent",
                "Region of interest",
                defaultValue=None,
            ),
            createOutput=True,
        )

    def reload(self, selected_layers, parameters, context, model_feedback):
        outputs = {}
        feedback = QgsProcessingMultiStepFeedback(len(selected_layers), model_feedback)
        carto_layer_filename = None
        for vlayer in selected_layers:
            layer_filename = vlayer.dataProvider().dataSourceUri()
            if "Carto" in layer_filename:
                index = layer_filename.index("|")
                carto_layer_filename = layer_filename[:index]
                break

        alg = ReloadIMLayer.createInstance()
        step_count = len(selected_layers)
        for i, vlayer in enumerate(selected_layers):
            feedback.setCurrentStep(i)
            if feedback.isCanceled():
                return {"success": False}

            layer_id = vlayer.id()
            output_key = LayerMetadata.get_layer_id(vlayer)
            project_hrn = LayerMetadata.get_project_hrn(vlayer)
            catalog_hrn = LayerMetadata.get_catalog_hrn(vlayer)
            params = {
                "HERE_CREDENTIALS_FILE": parameters.get("HERE_CREDENTIALS_FILE", ""),
                "project_hrn": project_hrn,
                "catalog_hrn": catalog_hrn,
                "qgis_layer_id": layer_id,
                "extent": parameters["extent"],
            }
            model_feedback.pushInfo("step {}/{}: {}".format(i, step_count, params))

            if project_hrn is None or catalog_hrn is None:
                model_feedback.reportError(
                    f"No project or catalog hrn in layer {layer_id} metadata"
                )
                outputs[output_key] = {}
                outputs[output_key]["success"] = False
                outputs[output_key][
                    "message"
                ] = f"No project or catalog hrn in layer {layer_id} metadata"
                continue
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
                outputs[output_key] = {}
                outputs[output_key]["success"] = False
                outputs[output_key]["error"] = repr(e)

            feedback.setCurrentStep(i + 1)

        if carto_layer_filename is not None:
            os.remove(carto_layer_filename)
        success = all([outputs[key]["success"] for key in outputs.keys()])
        return {"output": outputs, "success": success}

    def filterVisibleLayers(self, layers):
        layer_tree_root = QgsProject.instance().layerTreeRoot()
        visible = list(
            filter(
                lambda layer: layer_tree_root.findLayer(layer.id()).isVisible(),
                layers,
            )
        )
        return visible

    def processAlgorithm(self, parameters, context, feedback):
        invalid_status = self._check_invalid_credentials(parameters, feedback)
        if invalid_status:
            return invalid_status

        if iface is not None:
            selected_layers = iface.layerTreeView().selectedLayersRecursive()
            visible = self.filterVisibleLayers(selected_layers)
            return self.reload(visible, parameters, context, feedback)

        return {"output": {}, "message": "Non layer updated", "success": False}
