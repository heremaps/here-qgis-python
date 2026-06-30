# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.core import QgsProcessingParameterFile, QgsProject, QgsProviderRegistry

from here_qgis.api.basemap import BasemapAPI

from ..api_factory import create_api_for_processing
from ..settings import get_path
from .here_processing_base import HereProcessingAlgorithm
from .layer_metadata import LayerMetadata
from .uri_constructor import uri_constructor


class RefreshToken(HereProcessingAlgorithm):
    @classmethod
    def createInstance(cls) -> "HereProcessingAlgorithm":
        return cls()

    def displayName(self) -> str:
        return "Util: HERE Refresh Token"

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

    def iter_visible_node(self):
        root = QgsProject.instance().layerTreeRoot()

        for qnode in root.findLayers():
            if qnode.isVisible() and LayerMetadata.is_plugin_layer(qnode.layer()):
                yield qnode.layer()

    def processAlgorithm(self, parameters, context, feedback):
        layers = self.iter_visible_node()

        here_cred_path = parameters.get("HERE_CREDENTIALS_FILE", "")
        basemap_api = create_api_for_processing(BasemapAPI, here_cred_path)

        bearer_token = basemap_api.get_token()
        names = []
        not_updated = []
        for layer in layers:
            uri_components = QgsProviderRegistry.instance().decodeUri(
                layer.dataProvider().name(), layer.publicSource()
            )
            url = None
            if "url" in uri_components:
                url = uri_components["url"]
            else:
                not_updated.append(layer.name())
                continue
            uri = uri_constructor(url, bearer_token)
            metadata = layer.metadata()
            layer.setDataSource(uri, layer.name(), layer.providerType())
            layer.setMetadata(metadata)
            names.append(layer.name())

        return {
            "refreshed_layers": names,
            "not_refreshed_layers": not_updated,
            "success": True,
        }
