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
    Qgis,
    QgsFeature,
    QgsGeometry,
    QgsPalLayerSettings,
    QgsPointXY,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingOutputVectorLayer,
    QgsProcessingParameterFile,
    QgsProcessingParameterString,
    QgsSimpleMarkerSymbolLayer,
    QgsSingleSymbolRenderer,
    QgsSymbol,
    QgsTextBackgroundSettings,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor

from here_qgis.api.geocoding import GeocodeAPI, GeocodeObj

from ..api_factory import create_api_for_processing
from ..settings import get_path
from .here_processing_base import HereProcessingAlgorithm, HereProcessingException
from .processing_utils import LayerPostProcessor, new_field


class ProcessGeocoding(HereProcessingAlgorithm):
    @classmethod
    def createInstance(cls) -> "HereProcessingAlgorithm":
        return cls()

    def displayName(self) -> str:
        return "HERE Geocoding"

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

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
                "location",
                "Name of the location",
                multiLine=False,
                defaultValue="Am Kronberger Hang 8, 65824 Schwalbach am Taunus",
            )
        )

        self.addOutput(QgsProcessingOutputVectorLayer("output", "Geocoded layer"))

    def geocode_obj_to_dict(self, geocode_obj: GeocodeObj):
        flattened_dict = {}
        flattened_dict["hrn_id"] = geocode_obj.get_hrn_id()
        flattened_dict["resultType"] = geocode_obj.get_result_type()
        flattened_dict.update(geocode_obj.get_position())
        flattened_dict.update(geocode_obj.get_address())
        return flattened_dict

    def processAlgorithm(
        self,
        parameters: Dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ):
        """
        Here is where the processing itself takes place.
        """
        location_query = parameters["location"]

        here_cred_path = parameters.get("HERE_CREDENTIALS_FILE", "")
        geocoding_obj = create_api_for_processing(GeocodeAPI, here_cred_path)

        cached_response = geocoding_obj.geocode_request(location_query)
        if cached_response.is_empty():
            feedback.reportError("Response is empty")
            return {"error": "Response is empty", "success": False}
        geocode_response = cached_response.get_geocode_objects()

        geocoded_layer = QgsVectorLayer("Point?crs=EPSG:4326", location_query, "memory")

        if not geocoded_layer.isValid():
            raise HereProcessingException("Failed to create the vector layer.")

        pr = geocoded_layer.dataProvider()
        parsed_dict = self.geocode_obj_to_dict(cached_response.get_geocode_objects()[0])

        for keys, _values in parsed_dict.items():
            field = new_field(
                keys, QVariant.String
            )  # You can add more fields as needed
            pr.addAttributes([field])

        geocoded_layer.updateFields()

        for geocode_obj in geocode_response:
            object_dict = self.geocode_obj_to_dict(geocode_obj)
            point = QgsPointXY(
                geocode_obj.get_longitude(), geocode_obj.get_latitude()
            )  # Set the point coordinates
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPointXY(point))
            list_string = map(str, list(object_dict.values()))
            feature.setAttributes(list(list_string))
            pr.addFeature(feature)
        geocoded_layer.updateExtents()

        self.update_style(geocoded_layer)

        LayerPostProcessor.add_layer_into_context(context, geocoded_layer)
        feedback.pushInfo("Vector layer loaded successfully!")
        return {"layer_id": geocoded_layer.id(), "success": True}

    def postProcessAlgorithm(
        self, context: QgsProcessingContext, feedback: QgsProcessingFeedback
    ):
        for vlayer in LayerPostProcessor.get_layers_from_context(context):
            LayerPostProcessor.zoom_to_layer(vlayer)
        return {}

    def update_style(self, layer: QgsVectorLayer):
        # Create a symbol with a circle and a ring
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        symbol_layer = QgsSimpleMarkerSymbolLayer()
        symbol_layer.setSize(4)
        # Set dark blue color for the circle
        symbol_layer.setColor(QColor("dark blue"))
        # Append the circle symbol layer
        symbol.appendSymbolLayer(symbol_layer)
        # Add an outer ring
        ring_layer = QgsSimpleMarkerSymbolLayer()
        ring_layer.setSize(3)  # You can adjust the size of the ring
        ring_layer.setColor(QColor("light blue"))  # Set light blue color for the ring
        ring_layer.setStrokeColor(
            QColor("light blue")
        )  # Set the same dark blue color for the ring's border
        # Append the ring symbol layer
        symbol.appendSymbolLayer(ring_layer)
        # Set the symbol for the layer
        renderer = QgsSingleSymbolRenderer(symbol)
        layer.setRenderer(renderer)
        # Add labels
        label_settings = QgsPalLayerSettings()
        label_settings.isExpression = True
        label_settings.fieldName = (
            '''concat(array_get( string_to_array("'''
            + "label"
            + '''", ','),0),'\nCoordinates: ' + to_string("'''
            + "lat"
            + '''"), ', ' + to_string("'''
            + "lng"
            + """"))"""
        )
        label_settings.placement = Qgis.LabelPlacement.OverPoint
        label_settings.quadOffset = Qgis.LabelQuadrantPosition.AboveRight
        text_format = label_settings.format()
        text_format.setSize(10)  # Set the font size as needed
        text_format.setColor(QColor("black"))  # Set the font color as needed
        background_color = QgsTextBackgroundSettings()
        background_color.setFillColor(QColor("light gray"))
        background_color.setEnabled(True)
        text_format.setBackground(background_color)
        label_settings.setFormat(text_format)
        label_settings.centroidWhole = True
        label_settings.xOffset = 1.5
        # Set up the labeling on the layer
        layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))
        layer.setLabelsEnabled(True)
