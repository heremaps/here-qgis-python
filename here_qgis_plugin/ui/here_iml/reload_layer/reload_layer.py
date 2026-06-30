###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.core import QgsProviderRegistry  # noqa
from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer
from requests import HTTPError

from here_qgis.api.mapprojects import MapProjectsAPI

from ....api_factory import create_api_for_ui
from ....processing_toolbox.processing_utils import LayerMetadata, LayerPostProcessor
from ...here_qgis_processing.refresh_token_processing import refresh_token_processing
from ...here_qgis_processing.reload_layer_processing import (
    is_MM_project,
    reload_layer_processing,
)
from ...utils.settings_manager import get_sso_token, set_fallback_sso_token
from ..imlmap.imlmap_popup import CONTEXT, FEEDBACK
from ..message_bar import show_msg_bar_error, show_msg_bar_info, show_msg_bar_warning


class ReloadLayers:
    def __init__(self, iface):
        self.iface = iface
        self.continue_reload = True
        self.refresh_token_only = False

        self.valid_raster_layers = []
        self.valid_vector_layers = []
        self.invalid_layers = []
        self.layer_id_cat_hrn = {}

    # TODO: test case need for this function
    def mapping_layer_id_cat_hrn(self, layer):
        self.layer_id_cat_hrn[LayerMetadata.get_layer_id(layer)] = (
            LayerMetadata.get_catalog_hrn(layer)
        )

    def check_requirements(self):
        self.is_mm_project = is_MM_project()

        if self.is_mm_project:
            root = QgsProject.instance().layerTreeRoot()
            self.layers_to_reload = list(
                filter(
                    lambda layer: root.findLayer(layer.id()).isVisible(),
                    QgsProject.instance().mapLayers().values(),
                )
            )

            # TODO: comment it out if reloading MM UI project
            # self._set_token_from_mm_project()

        else:
            self.layers_to_reload = self.iface.layerTreeView().selectedLayersRecursive()

        if not self.layers_to_reload and not self.is_mm_project:
            show_msg_bar_warning(
                "No active layer selected.",
            )
            self.continue_reload = False
            return

        for layer in self.layers_to_reload:
            self.mapping_layer_id_cat_hrn(layer)

            if isinstance(layer, QgsRasterLayer):
                is_plugin_layer = LayerMetadata.is_plugin_layer(layer)

                if is_plugin_layer:
                    self.valid_raster_layers.append(layer)
                else:
                    self.invalid_layers.append(layer)

            elif isinstance(layer, QgsVectorLayer):
                hrn = LayerMetadata.get_project_hrn(layer)

                if hrn:
                    self.valid_vector_layers.append(layer)
                else:
                    self.invalid_layers.append(layer)

        if self.valid_raster_layers:
            self.refresh_token_only = True

        if self.invalid_layers and not (
            self.valid_vector_layers or self.valid_raster_layers
        ):
            names = [layer.name() for layer in self.invalid_layers]
            show_msg_bar_warning(
                f"Unrecognized layers: {', '.join(names)}.&nbsp;Skip reloading.",
            )
            self.continue_reload = False

        # Permission checks
        if self.valid_vector_layers:
            project_hrn_to_reload = [
                LayerMetadata.get_project_hrn(layer)
                for layer in self.valid_vector_layers
            ]
            project_hrn = next((hrn for hrn in project_hrn_to_reload if hrn), None)

            mp_api = create_api_for_ui(MapProjectsAPI, project_hrn)

            try:
                if not mp_api.has_read_permission():
                    show_msg_bar_warning(
                        f"You don't have access to project : {project_hrn}."
                    )
                    self.continue_reload = False
                else:
                    self.continue_reload = True
            except HTTPError as e:
                if e.response.status_code == 401:
                    show_msg_bar_warning("Token expired. Please login again.")
                else:
                    show_msg_bar_warning(f"Error occured: {str(e)}")

    def reload_layers(self):
        if self.continue_reload:
            canvas = self.iface.mapCanvas()
            extent = canvas.extent()
            crs = canvas.mapSettings().destinationCrs().authid()

            extent_str = (
                f"{extent.xMinimum()},{extent.xMaximum()},"
                f"{extent.yMinimum()},{extent.yMaximum()} [{crs}]"
            )

            input_layers_name = [
                layer.name().split(" ")[0].lower() for layer in self.valid_vector_layers
            ]
            self.input_layers_unique_name = set(input_layers_name)

            reload_layer_processing(
                extent_str=extent_str,
                context=CONTEXT,
                feedback=FEEDBACK,
                on_task_completed=self.on_task_completed,
            )

    def refresh_token(self):
        if self.refresh_token_only or self.is_mm_project:
            refresh_token_processing(
                context=CONTEXT,
                feedback=FEEDBACK,
                on_reload_completed=self.on_reload_completed,
            )

    def on_reload_completed(self, context, successful, results):
        if not (successful and results):
            show_msg_bar_warning(
                "Failed to refresh token. Please check the logs for details.",
            )
        else:
            show_msg_bar_info(
                "Token refreshed successfully.",
            )

    @classmethod
    def build_status_message(
        cls,
        output,
        input_layers_unique_name,
        layer_id_cat_hrn,
    ):
        success_groups = {}
        no_feature_groups = {}
        error_groups = {}

        for layer_id, layer_info in output.items():
            # Only process vector layers
            if layer_id not in input_layers_unique_name:
                # skip raster layer or unknown vector
                continue

            layer_name = layer_info.get("layer_name", layer_id)
            catalog_hrn = layer_id_cat_hrn.get(layer_id, "Unknown")

            if layer_info.get("success"):
                success_groups.setdefault(catalog_hrn, []).append(layer_name)
            elif layer_info.get("no_feature"):
                no_feature_groups.setdefault(catalog_hrn, []).append(layer_name)
            else:
                error_groups.setdefault(catalog_hrn, []).append(layer_name)

        # Status message
        status_parts = []
        if success_groups:
            success_text = " | ".join(
                f"{hrn}: {', '.join(layers)}" for hrn, layers in success_groups.items()
            )
            status_parts.append(f"Success: {success_text} |")

        if no_feature_groups:
            no_feature_text = " | ".join(
                f"{hrn}: {', '.join(layers)}"
                for hrn, layers in no_feature_groups.items()
            )
            status_parts.append(f"No Feature: {no_feature_text} |")

        if error_groups:
            error_text = " | ".join(
                f"{hrn}: {', '.join(layers)}" for hrn, layers in error_groups.items()
            )
            status_parts.append(f"Error: {error_text} |")

        message = "Status:\n" + "\n".join(status_parts)

        return {
            "message": message,
            "has_success": bool(success_groups),
            "has_no_feature": bool(no_feature_groups),
            "has_error": bool(error_groups),
        }

    def on_task_completed(self, context, params, successful, results):
        """Callback for when the processing task is successfully completed."""

        LayerPostProcessor.get_layers_from_context(context)
        if successful and results:
            # print(results)
            output = results.get("output", {})
            status = ReloadLayers.build_status_message(
                output,
                self.input_layers_unique_name,
                self.layer_id_cat_hrn,
            )

            message = status["message"]
            if status["has_error"]:
                show_msg_bar_error(message)
            elif status["has_success"] and not status["has_no_feature"]:
                show_msg_bar_info(message)
            else:
                show_msg_bar_warning(message)

        else:
            show_msg_bar_error(
                "Failed to load layer. Please check the logs for details."
            )

    def _set_token_from_mm_project(self):
        """Extract and apply token from MM project downloaded from MM UI.
        In this implementation, token is extracted from raster map tile
        """
        if not get_sso_token():
            layer_with_token = QgsProject.instance().mapLayersByName(
                "HERE Explore Day"
            )[
                0
            ]  # noqa
            uri_components = QgsProviderRegistry.instance().decodeUri(
                layer_with_token.dataProvider().name(),
                layer_with_token.publicSource(),  # noqa
            )
            token = uri_components["http-header:Authorization"].split(" ")[-1]
            set_fallback_sso_token(token)
