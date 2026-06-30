# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2023 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.core import (
    QgsProcessingOutputRasterLayer,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterString,
    QgsRasterLayer,
)

from here_qgis.api.basemap import BasemapAPI

from ..api_factory import create_api_for_processing
from ..settings import get_path
from .here_processing_base import HereProcessingAlgorithm
from .layer_metadata import LayerMetadata
from .processing_utils import LayerPostProcessor
from .uri_constructor import uri_constructor


class LoadBasemap(HereProcessingAlgorithm):
    IMAGE_FORMATS = ["png", "png8", "jpeg"]
    IMAGE_SIZES = ["256", "512"]
    MAP_TILE_STYLES = [
        "explore.day",
        "explore.night",
        "explore.satellite.day",
        "lite.day",
        "lite.night",
        "lite.satellite.day",
        "logistics.day",
        "satellite.day",
        "topo.day",
    ]
    # fmt: off
    # map languages
    LANGUAGES = [
        "ar", "as", "az", "be", "bg", "bn", "bs", "ca", "cs", "cy", "da", "de", "el",
        "en", "es", "et", "eu", "fi", "fo", "fr", "ga", "gl", "gn", "gu", "he", "hi",
        "hr", "hu", "hy", "id", "is", "it", "ja", "ka", "kk", "km", "kn", "ko", "ky",
        "lt", "lv", "mk", "ml", "mr", "ms", "mt", "my", "nl", "no", "or", "pa", "pl",
        "pt", "ro", "ru", "sk", "sl", "sq", "sr", "sv", "ta", "te", "th", "tr", "uk",
        "uz", "vi", "zh", "zh-Hant",
    ]
    # geopolitical views
    GEOPOLITICAL_VIEWS = [
        "AB", "AR", "CY", "EG", "GE", "GR", "IN", "KE", "MA", "NT", "OS", "PK", "PS",
        "RS", "RU", "SD", "SR", "SY", "TR", "TZ", "UY",
    ]
    # fmt: on

    @classmethod
    def createInstance(cls) -> "HereProcessingAlgorithm":
        return cls()

    def displayName(self) -> str:
        return "HERE Map Tile"

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """
        # HERE credentials.properties, it should be without scope (11.03.2024)
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
            QgsProcessingParameterEnum(
                "styles",
                "Select style",
                options=self.MAP_TILE_STYLES,
                allowMultiple=False,
                usesStaticStrings=True,
                defaultValue="explore.day",
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                "imageFormats",
                "Select image format",
                options=self.IMAGE_FORMATS,
                allowMultiple=False,
                usesStaticStrings=True,
                defaultValue="png",
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                "imageSizes",
                "Select image size",
                options=self.IMAGE_SIZES,
                allowMultiple=False,
                usesStaticStrings=True,
                defaultValue="256",
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                "feature",
                "Specify feature",
                multiLine=False,
                defaultValue=None,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                "langs",
                "Select language",
                options=self.LANGUAGES,
                allowMultiple=False,
                usesStaticStrings=True,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                "langs_sec",
                "Select language (secondary)",
                options=self.LANGUAGES,
                allowMultiple=False,
                usesStaticStrings=True,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                "pview",
                "Geopolitical view",
                options=self.GEOPOLITICAL_VIEWS,
                allowMultiple=False,
                usesStaticStrings=True,
                optional=True,
            )
        )

        self.addOutput(QgsProcessingOutputRasterLayer("output", "Raster layer"))

    def generate_layer_name(self, style):
        """
        Returns splitted and capitalized version of the selected style
        """
        layer_name = " ".join(word.capitalize() for word in style.split("."))

        return layer_name

    def processAlgorithm(self, parameters, context, feedback):
        """
        HERE is where the processing itself takes place.
        """

        here_cred_path = parameters.get("HERE_CREDENTIALS_FILE", "")
        basemap_api = create_api_for_processing(BasemapAPI, here_cred_path)

        maptile_id = self.parameterAsEnumString(parameters, "styles", context)
        url = basemap_api.generate_url(
            self.parameterAsEnumString(parameters, "imageFormats", context),
            self.parameterAsEnumString(parameters, "imageSizes", context),
            maptile_id,
            self.parameterAsString(parameters, "feature", context),
            self.parameterAsEnumString(parameters, "langs", context),
            self.parameterAsEnumString(parameters, "langs_sec", context),
            self.parameterAsEnumString(parameters, "pview", context),
        )
        # get token
        bearer_token = basemap_api.get_token()
        # Construct the WMS parameters
        uri = uri_constructor(url, bearer_token)
        # get layer name
        layer_name = self.generate_layer_name(maptile_id)
        # Create the raster layer
        layer = QgsRasterLayer(uri, f"HERE {layer_name}", "wms")

        # Add metadata
        LayerMetadata.set_source(layer, "", "", maptile_id, "maptile")
        if layer.isValid():
            # context.project().addMapLayer(layer, False)
            # root = context.project().layerTreeRoot()
            # root.addChildNode(QgsLayerTreeLayer(layer))
            LayerPostProcessor.add_layer_into_context(context, layer)
            feedback.pushInfo("Raster layer loaded successfully!")
            return {"layer_id": layer.id(), "success": True}
        return {"error": "Layer is not valid", "success": False}
