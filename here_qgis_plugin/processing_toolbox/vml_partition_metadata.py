# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from typing import Any, Dict

from geojson import FeatureCollection
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingOutputString,
    QgsProcessingOutputVectorLayer,
    QgsProcessingParameterEnum,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFile,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsVectorLayer,
)

from here_qgis.api.vml import VMLApi, VMLBoundingBox

from ..api_factory import create_api_for_processing
from ..settings import get_path, get_project_hrn, get_vml_catalog_hrn
from ..style_set import StyleConfig
from ..utils.files import make_unique_full_path
from .here_processing_base import HereProcessingAlgorithm
from .layer_metadata import LayerMetadata
from .processing_utils import LayerPostProcessor


class LoadPartitionVersionedLayer(HereProcessingAlgorithm):
    OUTPUT = "output"

    @classmethod
    def createInstance(cls):
        return cls()

    def displayName(self):
        return "VML: Load Partition Metadata"

    def initAlgorithm(self, configuration: Dict[str, Any] = None):
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
                "Specify project hrn",
                multiLine=False,
                defaultValue=get_project_hrn(),
                optional=True,
            )
        )

        # catalog hrn
        self.addParameter(
            QgsProcessingParameterString(
                "catalog_hrn",
                "Specify catalog hrn",
                multiLine=False,
                defaultValue=get_vml_catalog_hrn(),
            )
        )

        # version
        self.addParameter(
            QgsProcessingParameterNumber(
                "catalog_version",
                "Specify catalog version, use latest if not set",
                defaultValue=None,
                optional=True,
                minValue=0,
            )
        )

        # layer id
        self.addParameter(
            QgsProcessingParameterString(
                "layer_id", "Specify Layer id", multiLine=False, defaultValue="address"
            )
        )

        # extent
        self.addParameter(
            QgsProcessingParameterExtent(
                "extent", "Region of interest", defaultValue=None
            )
        )

        # zoom level
        self.addParameter(
            QgsProcessingParameterNumber(
                "level", "Zoom level", defaultValue=None, optional=True
            )
        )

        # style set
        self.addParameter(
            QgsProcessingParameterEnum(
                "style_set",
                "Select style set",
                options=StyleConfig.STYLE_GROUPS,
                allowMultiple=False,
                usesStaticStrings=False,
                defaultValue=StyleConfig.NO_STYLE_IDX,
            )
        )

        self.addOutput(
            QgsProcessingOutputVectorLayer(
                self.OUTPUT,
                "Vector Layer output",
            )
        )

        self.addOutput(
            QgsProcessingOutputString(
                "layer_id",
                "Vector Layer id",
            )
        )

        self.addOutput(
            QgsProcessingOutputString(
                "debug",
                "debug",
            )
        )

    def processAlgorithm(
        self,
        parameters: Dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> Dict[str, Any]:
        # get_logger(level=logging.DEBUG)

        bbox = VMLBoundingBox(
            level=parameters["level"] or 12,
            **self.get_bbox_from_params(parameters, "extent", context),
        )
        project_hrn = parameters["project_hrn"]

        here_cred_path = parameters.get("HERE_CREDENTIALS_FILE", "")
        api = create_api_for_processing(
            VMLApi, here_cred_path, project_hrn=parameters["project_hrn"]
        )

        catalog_hrn = self.parameterAsString(parameters, "catalog_hrn", context)
        layer_id = self.parameterAsString(parameters, "layer_id", context)
        catalog_version = parameters["catalog_version"]

        partitions = api.get_partitions_by_bbox_as_geojson(
            catalog_hrn,
            layer_id,
            bbox=bbox,
            version=catalog_version,
        )
        filename = make_unique_full_path("geojson")
        text = self.convert_partitions_to_file(partitions, filename, feedback)

        layer_name = "{} {}".format(layer_id, catalog_hrn.split(":")[-1])
        uri = f"{filename}"
        vlayer = QgsVectorLayer(uri, layer_name, "ogr")
        vlayer.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        LayerMetadata.set_source(
            vlayer, project_hrn, catalog_hrn, layer_id, "vml_metadata"
        )

        if not vlayer.isValid():
            return {"success": False}

        context.temporaryLayerStore().addMapLayer(vlayer)

        details = QgsProcessingContext.LayerDetails(
            layer_name, context.project(), self.OUTPUT
        )
        details.forceName = True
        context.addLayerToLoadOnCompletion(
            vlayer.id(),
            details,
        )

        return dict(
            output=vlayer.id(),
            layer_id=vlayer.id(),
            debug=text[:100],
            success=True,
        )

    def convert_partitions_to_file(
        self, partitions: FeatureCollection, filename: str, feedback
    ):
        text = str(partitions)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(text)
        return text

    def postProcessAlgorithm(
        self, context: QgsProcessingContext, feedback: QgsProcessingFeedback
    ) -> Dict[str, Any]:
        LayerPostProcessor.post_process(context, feedback)
        return {}
