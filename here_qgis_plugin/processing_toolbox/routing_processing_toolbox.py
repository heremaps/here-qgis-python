###############################################################################
#
# Copyright (c) 2023 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import json
import re
import time

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsGeometry,
    QgsMarkerSymbol,
    QgsPalLayerSettings,
    QgsPointXY,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingOutputVectorLayer,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterPoint,
    QgsProject,
    QgsSingleSymbolRenderer,
    QgsSymbol,
    QgsTextBackgroundSettings,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor

from here_qgis.api.routing import RoutingAPI

from ..settings import get_path
from ..ui.utils.settings_manager import get_sso_token
from .here_processing_base import HereProcessingAlgorithm
from .processing_utils import LayerPostProcessor, new_field


class ProcessRouting(HereProcessingAlgorithm):
    @classmethod
    def createInstance(cls) -> "HereProcessingAlgorithm":
        return cls()

    def displayName(self) -> str:
        return "HERE Routing"

    # @qgsfunction(args=0, group='Custom')
    def save_vector_file(self, geom_feature, layer_name):
        """
        Save vector data into vector file
        """

        timestr = time.strftime("%Y%m%d-%H%M%S")
        filename = f"{layer_name}_{timestr}.geojson"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(geom_feature, f, ensure_ascii=False)

        return filename

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # HERE credential file for authentication
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

        self.transport_modes = [
            "car",
            "pedestrian",
            "bicycle",
            "scooter",
            "taxi",
            "bus",
            "privateBus",
        ]

        self.addParameter(
            QgsProcessingParameterEnum(
                "transport_mode",
                "Select transport mode",
                options=self.transport_modes,
                defaultValue="car",
                allowMultiple=False,
            )
        )

        self.addParameter(
            QgsProcessingParameterPoint(
                "origin",
                "From Address (lon,lat)",
                defaultValue="11.594067,48.126073 [EPSG:4326]",
            )
        )

        self.addParameter(
            QgsProcessingParameterPoint(
                "destination",
                "To Address (lon,lat)",
                defaultValue="11.604277,48.142894 [EPSG:4326]",
            )
        )
        self.addOutput(QgsProcessingOutputVectorLayer("output", "Route layer"))
        self.addOutput(QgsProcessingOutputVectorLayer("output_nodes", "Nodes layer"))

    def parse_coordinates(self, input_coordinate):
        polyline_coordinates, crs = input_coordinate.split(" ")

        # keep only digits
        crs = re.sub(r"\D", "", crs)
        lon, lat = polyline_coordinates.split(",")

        point = QgsPointXY(float(lon), float(lat))

        if crs != "4326":
            transform = QgsCoordinateTransform(
                QgsCoordinateReferenceSystem("EPSG:" + str(crs)),
                QgsCoordinateReferenceSystem("EPSG:4326"),
                QgsProject.instance(),
            )
            point = transform.transform(point)
        lon, lat = point.x(), point.y()

        return lon, lat

    def processAlgorithm(self, parameters, context, feedback):
        # transport mode
        transport_mode = self.transport_modes[parameters["transport_mode"]]
        # parse polyline_coordinates from the input

        origin_lon, origin_lat = self.parse_coordinates(parameters["origin"])

        dest_lon, dest_lat = self.parse_coordinates(parameters["destination"])
        # request routing
        if parameters.get("HERE_CREDENTIALS_FILE", ""):
            routing_api = RoutingAPI(
                here_cred_path=parameters.get("HERE_CREDENTIALS_FILE", "")
            )
        else:
            routing_api = RoutingAPI(token=get_sso_token())

        cached_response = routing_api.routing_request(
            transport_mode, origin_lat, origin_lon, dest_lat, dest_lon
        )
        routing_obj = cached_response.get_routing_objects()[0]
        polyline_coordinates = routing_obj.get_polyline()

        # Create a new memory layer for the polyline
        layer_name = f"Routing Layers - {transport_mode} - 1"
        crs = QgsProject.instance().crs()  # Use the project CRS
        polyline_layer = QgsVectorLayer(
            "LineString?crs=" + crs.authid(), layer_name, "memory"
        )
        provider = polyline_layer.dataProvider()

        transform = None

        if crs.authid() != "EPSG:4326":
            transform = QgsCoordinateTransform(
                QgsCoordinateReferenceSystem("EPSG:4326"),
                QgsCoordinateReferenceSystem(crs.authid()),
                QgsProject.instance(),
            )

        # parse points with transform if necessary
        points = []
        total_coors = len(polyline_coordinates)
        for x, y in polyline_coordinates:
            point = (
                transform.transform(QgsPointXY(y, x))
                if transform is not None
                else QgsPointXY(y, x)
            )

            points.append(point)

        origin_point = points[0]
        dest_point = points[total_coors - 1]
        summary = routing_obj.get_summary()

        for keys, _values in summary.items():
            field = new_field(keys, QVariant.Int)
            provider.addAttributes([field])
        polyline_layer.updateFields()

        # Create a new feature
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromPolylineXY(points))
        feature.setAttributes(list(summary.values()))
        provider.addFeature(feature)

        polyline_layer.updateExtents()

        self.update_style_route_layer(polyline_layer)

        # Create a memory layer for points
        layer_name = "Starting and Destination points"
        points_layer = QgsVectorLayer("Point?crs=" + crs.authid(), layer_name, "memory")

        points_provider = points_layer.dataProvider()
        field = new_field("type", QVariant.String)
        points_provider.addAttributes([field])
        # Create a feature for the starting point
        start_feature = QgsFeature()
        start_feature.setGeometry(QgsGeometry.fromPointXY(origin_point))
        start_feature.setAttributes(["A"])
        points_provider.addFeature(start_feature)
        # Create a feature for the destination point
        end_feature = QgsFeature()
        end_feature.setGeometry(QgsGeometry.fromPointXY(dest_point))
        end_feature.setAttributes(["B"])
        points_provider.addFeature(end_feature)
        points_layer.updateFields()

        self.update_style_points_layer(points_layer)

        LayerPostProcessor.add_layer_into_context(context, points_layer)
        LayerPostProcessor.add_layer_into_context(context, polyline_layer)

        return {
            "output": polyline_layer.id(),
            "output_nodes": points_layer.id(),
            "success": True,
        }

    def postProcessAlgorithm(
        self, context: QgsProcessingContext, feedback: QgsProcessingFeedback
    ):
        for vlayer in LayerPostProcessor.get_layers_from_context(context):
            LayerPostProcessor.zoom_to_layer(vlayer)
        return {}

    def update_style_route_layer(self, polyline_layer):
        # Define a simple line symbol
        line_symbol = QgsSymbol.defaultSymbol(polyline_layer.geometryType())
        line_symbol.setColor(
            QColor("light green")
        )  # Set line color (blue in this example)
        line_symbol.setWidth(2)  # Set line width
        # Apply the symbol to the layer
        polyline_layer.renderer().setSymbol(line_symbol)
        label_settings = QgsPalLayerSettings()
        label_settings.isExpression = True
        label_settings.fieldName = """concat(to_string(ceil("duration"/60)),
        ' mins', ' ; ', to_string("length"), ' m')
        """
        label_settings.placement = Qgis.LabelPlacement.Line
        # label_settings.quadOffset = Qgis.LabelQuadrantPosition.AboveRight
        text_format = label_settings.format()
        text_format.setSize(40)  # Set the font size as needed
        text_format.setColor(QColor("black"))  # Set the font color as needed
        background_color = QgsTextBackgroundSettings()
        background_color.setFillColor(QColor("light green"))
        background_color.setEnabled(True)
        text_format.setBackground(background_color)
        label_settings.setFormat(text_format)
        label_settings.centroidWhole = True
        label_settings.xOffset = 1.5
        # Set up the labeling on the layer
        polyline_layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))
        polyline_layer.setLabelsEnabled(True)

    def update_style_points_layer(self, points_layer: QgsVectorLayer):
        symbol = QgsMarkerSymbol.createSimple(
            {"name": "circle", "size": "4", "color": "dark blue"}
        )
        renderer = QgsSingleSymbolRenderer(symbol)
        points_layer.setRenderer(renderer)
        # Set up labeling with rules
        label_settings = QgsPalLayerSettings()
        label_settings.fieldName = "type"
        label_settings.placement = Qgis.LabelPlacement.OverPoint
        label_settings.quadOffset = Qgis.LabelQuadrantPosition.AboveRight
        text_format = label_settings.format()
        text_format.setSize(40)  # Set the font size as needed
        text_format.setColor(QColor("dark"))  # Set the font color as needed
        label_settings.setFormat(text_format)
        label_settings.centroidWhole = True
        label_settings.xOffset = 1.5
        # Set up the labeling on the layer
        points_layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))
        points_layer.setLabelsEnabled(True)
