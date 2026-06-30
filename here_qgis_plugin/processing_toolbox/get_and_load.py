###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os
from typing import List

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsExpression,
    QgsFeatureRequest,
    QgsProcessingContext,
    QgsVectorLayer,
    QgsWkbTypes,
)

from here_qgis.io.layer_storage import LayerStorage

from ..style_set import StyleConfig
from .file_type import FileType
from .get_features import get_features
from .layer_metadata import LayerMetadata
from .processing_utils import LayerPostProcessor, ctlg_hrn_parser, wkb_type_to_geom_type

# default IML
DEFAULT_IML_LAYERS = [
    "address",
    "admin",
    "building",
    "carto",
    "place",
    "relation",
    "topology",
]


class GetAndLoad:
    def __init__(
        self, bbox, parameters, feedback, context, iml_context="default", query=""
    ):
        self.bbox = bbox
        self.parameters = parameters
        self.feedback = feedback
        self.context = context
        self.iml_context = iml_context
        self.query = query

    def get_features(self):
        self.layer_feature, self.layer_name = get_features(
            self.bbox, self.parameters, self.feedback, self.iml_context, self.query
        )
        self.folder_name, self.group_name = ctlg_hrn_parser(
            self.parameters["catalog_hrn"]
        )

        return self.layer_name, self.folder_name, self.layer_feature

    def load_to_qgis(
        self,
        imlsave_obj: LayerStorage,
        filetype: str = FileType.GEOPACKAGE.name,
        density_iml=False,
    ):
        """
        Function loads data to QGIS

        :params:
            imlsave_obj: LayerStorage object

            filetype: FileType enum
        """
        imlsave_obj.process_features()
        if filetype == FileType.GEOPACKAGE.name:
            geom_types_filenames = imlsave_obj.from_features_to_geopackage()
        elif filetype == FileType.GEOJSON.name:
            geom_types_filenames = imlsave_obj.from_features_to_geojson()
        else:
            raise Exception("Wrong file type selected")

        layers = self.load_layer(
            geom_types_filenames,
            self.layer_name,
            self.parameters["layer_id"],
            self.parameters["style_set"],
            # TODO: if there will be more file types,
            # load_layer needs to be adjusted
            filetype,
            self.group_name,
            self.context,
            density_iml=density_iml,
        )

        if len(layers) > 0:
            layer_ids = [i.id() for i in layers]
            layer_names = [i.name() for i in layers]
            return {
                "layer_id": layer_ids,
                "layer_name": layer_names,
                "bbox": self.bbox,
                "group_name": self.group_name,
                "layers": layers,
            }

        else:
            return {}

    def _is_empty_file(self, uri: str):
        if "|" in uri:
            uri = uri.split("|")[0]
        if os.path.getsize(uri) == 0:
            return True
        return False

    def create_layers(
        self,
        temp_filename: str,
        iml_disp_name: str,
        layer_id: str,
        style_set: str,
        geom_type: str,
        filetype: str,
        group_name: str,
        context: QgsProcessingContext,
        density_iml=False,
    ) -> List[QgsVectorLayer]:
        """
        Function used to process layers.

        """
        uri = temp_filename
        if self._is_empty_file(uri):
            return []
        # if filetype == FileType.GEOJSON.name:
        #     uri += "|option:GEOMETRY_AS_COLLECTION=yes"
        options = QgsVectorLayer.LayerOptions()
        options.fallbackCrs = QgsCoordinateReferenceSystem("EPSG:4326")
        options.fallbackWkbType = getattr(Qgis.WkbType, geom_type)
        iml_layer = QgsVectorLayer(uri, iml_disp_name, "ogr", options=options)
        iml_layer.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))

        self.init_layer_metadata(
            iml_layer,
            self.parameters["project_hrn"],
            self.parameters["catalog_hrn"],
            layer_id,
        )

        if density_iml:
            geometry_type = QgsWkbTypes.displayString(iml_layer.wkbType())
            layerIds = iml_layer.uniqueValues(
                iml_layer.fields().indexFromName("layerId")
            )
            layers = []
            for layerId in layerIds:
                value_clean = layerId.strip('"')
                unique_disp_name = f"{iml_layer.name()} - {value_clean.capitalize()}"
                temp_layer = QgsVectorLayer(
                    f"{geometry_type}?crs=EPSG:4326", unique_disp_name, "memory"
                )

                self.init_layer_metadata(
                    temp_layer,
                    self.parameters["project_hrn"],
                    self.parameters["catalog_hrn"],
                    layer_id,
                )
                # temp_layer fields
                temp_layer_data_provider = temp_layer.dataProvider()
                temp_layer_data_provider.addAttributes(iml_layer.fields())
                temp_layer.updateFields()

                # temp_layer subset features
                expression = QgsExpression(f"layerId = '{layerId}'")
                request = QgsFeatureRequest(expression)
                temp_layer_data_provider.addFeatures(iml_layer.getFeatures(request))
                temp_layer.updateExtents()

                # add layer to context
                LayerPostProcessor.add_layer_into_context(context, temp_layer)

                # add metadata to temp_layer
                style_set_info = StyleConfig.to_info(
                    layer_id, style_set, wkb_type_to_geom_type(geom_type)
                )
                style_set_info_str = StyleConfig.style_set_to_str(style_set_info)
                LayerPostProcessor.set_style(style_set_info_str, temp_layer)
                LayerPostProcessor.set_filetype(filetype, temp_layer)
                LayerPostProcessor.set_group_name(group_name, temp_layer)
                LayerPostProcessor.set_iml_context(self.iml_context, temp_layer)

                layers.append(temp_layer)

            return layers
        else:
            # add layer to context
            LayerPostProcessor.add_layer_into_context(context, iml_layer)

            # apply styling only to default IMLayers
            if layer_id.lower() in DEFAULT_IML_LAYERS:
                style_set_info = StyleConfig.to_info(
                    layer_id, style_set, wkb_type_to_geom_type(geom_type)
                )
                style_set_info_str = StyleConfig.style_set_to_str(style_set_info)
                LayerPostProcessor.set_style(style_set_info_str, iml_layer)
            LayerPostProcessor.set_filetype(filetype, iml_layer)
            LayerPostProcessor.set_group_name(group_name, iml_layer)
            LayerPostProcessor.set_iml_context(self.iml_context, iml_layer)

            return [iml_layer]

    def init_layer_metadata(self, iml_layer, project_hrn, catalog_hrn, layer_id):
        LayerMetadata.set_source(iml_layer, project_hrn, catalog_hrn, layer_id)

    def load_layer(
        self,
        geom_types_filenames,
        layer_name,
        iml_id,
        style_set,
        filetype,
        group_name,
        context,
        density_iml=False,
    ):
        layers = []
        for geom_type, temp_filename in geom_types_filenames.items():
            temp_filename_l = (
                temp_filename
                if filetype == FileType.GEOJSON.name
                else (
                    f"{temp_filename}|"
                    f"layername={layer_name.replace(' ', '_')}_{geom_type}"
                )
            )
            iml_disp_name = f"{layer_name} - {geom_type}"
            layers.extend(
                self.create_layers(
                    temp_filename_l,
                    iml_disp_name,
                    iml_id,
                    style_set,
                    geom_type,
                    filetype,
                    group_name,
                    context,
                    density_iml,
                )
            )
        return layers
