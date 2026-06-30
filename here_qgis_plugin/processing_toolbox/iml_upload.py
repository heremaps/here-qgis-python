###############################################################################
#
# Copyright (c) 2023 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################
from collections import OrderedDict

from qgis.core import (
    QgsProcessing,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorLayer,
)
from typing_extensions import deprecated

from .here_processing_base import HereProcessingAlgorithm


@deprecated("use MapMakingUpload instead")
class UploadIMLayer(HereProcessingAlgorithm):
    @classmethod
    def createInstance(cls):
        return cls()

    def displayName(self) -> str:
        return "Upload IML to MapMaking"

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "upload_layer",
                "Upload layer",
                types=[QgsProcessing.SourceType.TypeVectorAnyGeometry],
                defaultValue=None,
            )
        )

        # project hrn
        self.addParameter(
            QgsProcessingParameterString(
                "project_hrn",
                "Specify project:hrn",
                multiLine=False,
                defaultValue="",
            )
        )

        # layer id
        self.addParameter(
            QgsProcessingParameterString(
                "layer_id", "Specify layer id", multiLine=False, defaultValue="topology"
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        HERE is where the processing itself takes place.
        """

        # Get the provider
        layer_upload = parameters["upload_layer"]
        prov = layer_upload.dataProvider()
        # Get fields names with the order
        fields = [field.name() for field in prov.fields()]
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": OrderedDict(zip(fields, i.attributes())),
                    "geometry": i.geometry().asJson(),
                }
                for i in layer_upload.getFeatures()
            ],
        }

        # TODO: upload to iml, merge with mapmaking_upload

        return {"output": len(geojson["features"])}
