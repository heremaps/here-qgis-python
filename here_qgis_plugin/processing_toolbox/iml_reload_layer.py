###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from typing import Any, Dict, Optional

from geojson import FeatureCollection
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsLayerTreeLayer,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFile,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorLayer,
    QgsProject,
    QgsVectorLayer,
)

from here_qgis.helper_functions import CLICK_KEEP_UNAVAILABLE_LAYERS, EMPTY_FILE
from here_qgis.io.layer_storage import LayerStorage

from ..settings import get_catalog_hrn, get_path, get_project_hrn
from ..style_set import StyleConfig
from .get_features import get_features
from .here_processing_base import HereProcessingAlgorithm
from .layer_metadata import LayerMetadata, LayerMetadataPluginV1
from .processing_utils import LayerPostProcessor, wkb_type_to_geom_type
from .reload_layer_helpers import get_features_ids, trim_filename


class ReloadIMLayer(HereProcessingAlgorithm):
    @classmethod
    def createInstance(cls):
        return cls()

    def displayName(self) -> str:
        return "IML: Reload IML Layer"

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
            QgsProcessingParameterString(
                "project_hrn",
                "Specify Project HRN",
                multiLine=False,
                defaultValue=get_project_hrn(),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                "catalog_hrn",
                "Specify catalog:hrn",
                multiLine=False,
                defaultValue=get_catalog_hrn(),
            )
        )

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "qgis_layer_id",
                "Specify which layer should be reloaded",
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

    def increment_layer(
        self,
        vlayer: QgsVectorLayer,
        selected_layer_filename,
        is_empty_layer,
        parameters,
        context,
        feedback,
    ) -> tuple[
        Optional[str], Optional[int], Optional[str], Optional[bool], Optional[dict]
    ]:
        """
        Load new features to the layer.

        This function adds new features from the same project and catalog
        as there were loaded before.
        It creates a new file with combined old and new data.

        Returns:
            If everything worked correct:
                layer name, number of combined features, new filename,
                    is carto, (geom_type, filename) string
            If no new features were added:
                "", 0, "", False, None
            If layer is not a plugin layer:
                None, None, None, None, None
        """

        if LayerMetadata.is_plugin_layer(vlayer):
            selected_features = None
            if not is_empty_layer:
                selected_features = vlayer.getFeatures()
            is_v1_layer = LayerMetadataPluginV1.is_V1_layer(vlayer)
            is_reloaded = bool(LayerMetadata.get_reloaded(vlayer))
            if is_v1_layer and is_reloaded:
                first_id_col, second_id_col = "id", "xyz_id"
            elif is_v1_layer:
                first_id_col, second_id_col = "xyz_id", None
            else:
                first_id_col, second_id_col = "id", None

            selected_features_ids = []
            if not is_empty_layer:
                selected_features_ids = get_features_ids(
                    selected_features,
                    first_id_col=first_id_col,
                    second_id_col=second_id_col,
                )

            parameters["layer_id"] = LayerPostProcessor.detect_feature_type(vlayer)

            bbox = self.get_bbox_from_params(parameters, "extent", context)
            iml_context = LayerPostProcessor.get_iml_context(vlayer)
            layer_feature, layer_name = get_features(
                bbox, parameters, feedback, iml_context
            )
            if not is_empty_layer:
                layer_feature = list(
                    filter(
                        lambda f: f["id"] not in selected_features_ids,
                        layer_feature["features"],
                    )
                )

            if len(layer_feature) > 0:
                feature_collection = FeatureCollection(layer_feature)
                if is_empty_layer:
                    imlsave_obj = LayerStorage(
                        layer_name,
                        LayerMetadata.get_catalog_hrn(vlayer),
                        feature_collection,
                    )
                else:
                    imlsave_obj = LayerStorage(layer_name, "", feature_collection)
                selected_layer_filename = trim_filename(
                    is_v1_layer, is_reloaded, selected_layer_filename
                )

                new_filename, is_carto, geom_filenames = (
                    imlsave_obj.add_features_to_file(
                        selected_layer_filename,
                        vlayer.name(),
                        is_v1_layer,
                        is_reloaded,
                    )
                )
                if new_filename is None:
                    return "", 0, "", False, None

                return (
                    layer_name,
                    len(feature_collection["features"]),
                    new_filename,
                    is_carto,
                    geom_filenames,
                )
            else:
                return "", 0, "", False, None
        return None, None, None, None, None

    def processAlgorithm(self, parameters, context, feedback):
        invalid_status = self._check_invalid_credentials(parameters, feedback)
        if invalid_status:
            return invalid_status

        selected_layer: QgsVectorLayer = context.project().mapLayer(
            parameters["qgis_layer_id"]
        )
        selected_layer_filename = selected_layer.dataProvider().dataSourceUri()

        is_empty_layer = False
        if (
            selected_layer_filename == EMPTY_FILE
            or selected_layer_filename == CLICK_KEEP_UNAVAILABLE_LAYERS
        ):
            is_empty_layer = True
            parameters["project_hrn"] = LayerMetadata.get_project_hrn(selected_layer)

        is_geopackage = ".gpkg" in selected_layer_filename
        self.group_name = ""
        self.index = 0
        self.cartos = []

        if not is_geopackage and not is_empty_layer:
            return {"error": "Only supported file type is GeoPackage", "success": False}

        layer_name, feature_len, new_filename, is_carto, geom_filenames = (
            self.increment_layer(
                selected_layer,
                selected_layer_filename,
                is_empty_layer,
                parameters,
                context,
                feedback,
            )
        )
        self.group_name = LayerPostProcessor.get_group_name(selected_layer)
        if is_empty_layer and is_carto:
            root = QgsProject.instance().layerTreeRoot()
            group = root.findGroup(self.group_name)

            for key in geom_filenames.keys():
                new_carto = QgsVectorLayer(
                    f"{new_filename}|layername={layer_name.replace(' ', '_')}_{key}",
                    f"{layer_name} - {key}",
                    "ogr",
                )
                LayerMetadata.copy_metadata(selected_layer, new_carto)
                style_set_info = StyleConfig.to_info(
                    "carto",
                    "Standard",
                    wkb_type_to_geom_type(key),
                )
                style_set_info_str = StyleConfig.style_set_to_str(style_set_info)
                LayerPostProcessor.set_style(style_set_info_str, new_carto)
                LayerPostProcessor.update_style(new_carto)
                new_carto.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
                group.insertChildNode(0, QgsLayerTreeLayer(new_carto))
                self.cartos.append(new_carto)

            context.project().instance().addMapLayers(self.cartos, addToLegend=False)
            if selected_layer:
                group.removeLayer(selected_layer)
                selected_layer.deleteLater()
            feedback.pushInfo(
                f"Layer {layer_name} was replaced by {len(self.cartos)} layers"
            )
            return {
                "layer_name": layer_name,
                "new_layers_num": len(self.cartos),
                "new_layers_ids": list(map(lambda c: c.id(), self.cartos)),
                "new_features_number": feature_len,
                "message": (
                    f"Layer {layer_name} was replaced by {len(self.cartos)} layers"
                ),
                "success": True,
            }

        if layer_name is None:
            return {
                "error": (
                    f"Layer {selected_layer.name()} is from other source than plugin!"
                ),
                "success": False,
            }

        if layer_name == "":
            return {
                "error": f"No new features loaded into {selected_layer.name()} layer",
                "no_feature": True,
                "success": False,
            }

        LayerMetadata.set_reloaded(selected_layer)

        selected_layer_filename_base = selected_layer_filename.split("|")[0]

        selected_layer.setDataSource(
            selected_layer.source().replace(selected_layer_filename_base, new_filename),
            selected_layer.name(),
            selected_layer.providerType(),
        )
        selected_layer.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        if is_empty_layer:
            selected_layer.setName(
                f"{selected_layer.name()} - {list(geom_filenames.keys())[0]}"
            )
            LayerPostProcessor.update_style(selected_layer)
            selected_layer.triggerRepaint()

        LayerPostProcessor.mark_dangling_layer(selected_layer, selected_layer_filename)
        return {
            "layer_name": layer_name,
            "new_features_number": feature_len,
            "new_layers_num": None,
            "new_layers_ids": None,
            "message": f"Layer {layer_name} reloaded",
            "success": True,
        }

    def postProcessAlgorithm(
        self, context: QgsProcessingContext, feedback: QgsProcessingFeedback
    ) -> Dict[str, Any]:
        LayerPostProcessor.post_process(context, feedback)
        LayerPostProcessor.remove_dangling_layers_from_context(context)
        return {}
