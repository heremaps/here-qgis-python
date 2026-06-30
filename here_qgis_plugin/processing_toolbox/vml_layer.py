# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import json
from typing import Any, Dict, Final, NamedTuple, Tuple

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingOutputString,
    QgsProcessingOutputVectorLayer,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFile,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsVectorLayer,
)

from here_qgis.api.vml import VMLApi, VMLBoundingBox, is_valid_partition_id

from ..api_factory import create_api_for_processing
from ..settings import get_vml_catalog_hrn
from ..style_set import StyleConfig
from ..utils.files import make_unique_full_path
from .here_processing_base import HereProcessingAlgorithm
from .layer_metadata import LayerMetadata
from .processing_utils import FileType, LayerPostProcessor, get_geom_type_str


class LoadVersionedLayer(HereProcessingAlgorithm):
    class Params(NamedTuple):
        CATALOG_HRN: Any
        EXTENT: Any
        LAYER_ID: Any
        HERE_CREDENTIALS_FILE: Any
        STYLE_SET: Any
        PROJECT_HRN: Any
        IS_FLATTEN: Any
        LEVEL: Any
        PARTITION_IDS: Any
        CATALOG_VERSION: Any

    class Output(NamedTuple):
        OUTPUT: Any
        LAYER_ID: Any
        DEBUG: Any
        EXTENT: Any
        FEAT_CNT: Any

    PARAMS: Final[Params] = Params(**{k: k for k in Params._fields})
    OUTPUT: Final[Output] = Output(**{k: k for k in Output._fields})

    @classmethod
    def createInstance(cls):
        return cls()

    def displayName(self):
        return "VML: Load Versioned Layer"

    def initAlgorithm(self, configuration: Dict[str, Any] = None):
        print("initAlgorithm", configuration)
        cls = LoadVersionedLayer

        # Specify HERE credentials file
        self.addParameter(
            QgsProcessingParameterFile(
                cls.PARAMS.HERE_CREDENTIALS_FILE,
                "Specify HERE credentials file",
                behavior=QgsProcessingParameterFile.Behavior.File,
                fileFilter="All Files (*.*)",
                defaultValue=None,
                optional=True,
            )
        )

        # project hrn
        self.addParameter(
            QgsProcessingParameterString(
                cls.PARAMS.PROJECT_HRN,
                "Specify project hrn",
                multiLine=False,
                defaultValue="hrn:here:authorization::olp-here:project/qgis-plugin-dev",
                optional=True,
            )
        )

        # Specify catalog:hrn
        self.addParameter(
            QgsProcessingParameterString(
                cls.PARAMS.CATALOG_HRN,
                "Specify catalog hrn",
                multiLine=False,
                defaultValue=get_vml_catalog_hrn(),
            )
        )

        # version
        self.addParameter(
            QgsProcessingParameterNumber(
                cls.PARAMS.CATALOG_VERSION,
                "Specify catalog version, use latest if not set",
                defaultValue=None,
                optional=True,
                minValue=0,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                cls.PARAMS.LAYER_ID,
                "Specify Layer id",
                multiLine=False,
                defaultValue="topology",
            )
        )

        # Region of interest
        self.addParameter(
            QgsProcessingParameterExtent(
                cls.PARAMS.EXTENT,
                "Region of interest",
                defaultValue=None,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                cls.PARAMS.PARTITION_IDS,
                "Partition Ids (comma-separated list)",
                defaultValue="",
                optional=True,
            )
        )

        # zoom level
        self.addParameter(
            QgsProcessingParameterNumber(
                cls.PARAMS.LEVEL,
                "Zoom level",
                defaultValue=None,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                cls.PARAMS.STYLE_SET,
                "Select style set",
                options=StyleConfig.STYLE_GROUPS,
                allowMultiple=False,
                usesStaticStrings=False,
                defaultValue=StyleConfig.NO_STYLE_IDX,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                cls.PARAMS.IS_FLATTEN,
                "Flatten nested JSON string (GDAL >= 3.8",
                defaultValue=False,
            )
        )

        self.addOutput(
            QgsProcessingOutputVectorLayer(
                cls.OUTPUT.OUTPUT,
                "Vector Layer output",
            )
        )

        self.addOutput(
            QgsProcessingOutputString(
                cls.OUTPUT.LAYER_ID,
                "Vector Layer id",
            )
        )

        self.addOutput(
            QgsProcessingOutputString(
                cls.OUTPUT.DEBUG,
                "debug",
            )
        )

    def checkParameterValues(
        self, parameters: Dict[str, Any], context: QgsProcessingContext
    ) -> Tuple[bool, str]:
        ok, msg = super(HereProcessingAlgorithm, self).checkParameterValues(
            parameters, context
        )
        if not ok:
            return ok, msg
        ok_spatial = bool(
            parameters.get(self.PARAMS.EXTENT)
            or parameters.get(self.PARAMS.PARTITION_IDS)
        )
        msg_spatial = (
            "Either extent or partition ids parameter must be provided"
            if not ok_spatial
            else ""
        )
        if not ok_spatial:
            return ok_spatial, msg_spatial

        partition_ids = self.parameterAsString(
            parameters, self.PARAMS.PARTITION_IDS, context
        )
        partition_ids = [p.strip() for p in partition_ids.split(",") if p.strip()]
        invalid_partition_ids = [
            tile_id for tile_id in partition_ids if not is_valid_partition_id(tile_id)
        ]
        ok_partition_ids = not len(invalid_partition_ids)
        msg_partition_ids = (
            "Invalid partition ids ({}): {}".format(
                len(invalid_partition_ids), ",".join(invalid_partition_ids)
            )
            if not ok_partition_ids
            else ""
        )
        return ok_partition_ids, msg_partition_ids

    # unused
    def preprocessParameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        params = super().preprocessParameters(parameters)
        print("preprocessParameters", params)
        return params

    def prepareAlgorithm(
        self,
        parameters: Dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> bool:
        print("prepareAlgorithm", parameters)
        ok, msg = self.checkParameterValues(parameters, context)
        if not ok:
            raise QgsProcessingException(msg)
        ok = super().prepareAlgorithm(parameters, context, feedback)
        return ok

    def processAlgorithm(
        self,
        parameters: Dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> Dict[str, Any]:
        # ## DEBUG
        # import logging
        # from ..utils.logging import get_logger
        # get_logger(level=logging.DEBUG)
        print("processAlgorithm", parameters)

        VALUES = self.Params(
            CATALOG_HRN=self.parameterAsString(
                parameters, self.PARAMS.CATALOG_HRN, context
            ),
            LAYER_ID=self.parameterAsString(parameters, self.PARAMS.LAYER_ID, context),
            HERE_CREDENTIALS_FILE=self.parameterAsFile(
                parameters, self.PARAMS.HERE_CREDENTIALS_FILE, context
            ),
            STYLE_SET=self.parameterAsInt(parameters, self.PARAMS.STYLE_SET, context),
            PROJECT_HRN=self.parameterAsString(
                parameters, self.PARAMS.PROJECT_HRN, context
            ),
            IS_FLATTEN=self.parameterAsBoolean(
                parameters, self.PARAMS.IS_FLATTEN, context
            ),
            LEVEL=parameters[self.PARAMS.LEVEL],
            CATALOG_VERSION=parameters.get(self.PARAMS.CATALOG_VERSION, None),
            PARTITION_IDS=parameters.get(self.PARAMS.PARTITION_IDS, ""),
            EXTENT=parameters.get(self.PARAMS.EXTENT, None),
        )

        catalog_version = VALUES.CATALOG_VERSION

        bbox = self.get_bbox_from_params(parameters, self.PARAMS.EXTENT, context)

        vml_bbox = VMLBoundingBox(level=VALUES.LEVEL or 12, **bbox)
        project_hrn = VALUES.PROJECT_HRN

        api = create_api_for_processing(
            VMLApi, VALUES.HERE_CREDENTIALS_FILE, project_hrn=project_hrn
        )
        catalog_hrn = VALUES.CATALOG_HRN
        layer_id = VALUES.LAYER_ID
        # feedback.pushInfo(str(api.get_layer(catalog_hrn, layer_id).get_details()))

        partition_ids = VALUES.PARTITION_IDS
        partition_ids = [p.strip() for p in partition_ids.split(",") if p.strip()]

        if partition_ids:
            parsed_blobs = api.get_features_by_partition_ids(
                catalog_hrn, layer_id, partition_ids, version=catalog_version
            )
        else:
            parsed_blobs = api.get_features_by_bbox(
                catalog_hrn, layer_id, bbox=vml_bbox, version=catalog_version
            )
        filename = make_unique_full_path("geojson")
        feat_cnt = self.convert_blob_to_file(parsed_blobs, filename, feedback)
        if not feat_cnt:
            return {"success": False}

        # ## DEBUG
        # text = ""
        # filename = (
        #     "~home/AppData/Roaming/QGIS/QGIS3/profiles/default/"
        #     "here_qgis_plugin_dev_local/tmp/sample.geojson")

        layer_name = "{} {}".format(layer_id, catalog_hrn.split(":")[-1])
        uri = f"{filename}|option:AUTODETECT_JSON_STRINGS=no"
        if VALUES.IS_FLATTEN:
            uri += "|option:FLATTEN_NESTED_ATTRIBUTES=yes"
        vlayer = QgsVectorLayer(uri, layer_name, "ogr")
        vlayer.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        LayerMetadata.set_source(vlayer, project_hrn, catalog_hrn, layer_id, "VML")

        if not vlayer.isValid():
            return {"success": False}

        context.temporaryLayerStore().addMapLayer(vlayer)

        details = QgsProcessingContext.LayerDetails(
            layer_name, context.project(), self.OUTPUT.OUTPUT
        )
        details.forceName = True
        context.addLayerToLoadOnCompletion(
            vlayer.id(),
            details,
        )

        style_set_info = StyleConfig.to_info(
            layer_id, VALUES.STYLE_SET, get_geom_type_str(vlayer)
        )
        style_set_info_str = StyleConfig.style_set_to_str(style_set_info)
        LayerPostProcessor.set_style(style_set_info_str, vlayer)
        LayerPostProcessor.set_filetype(FileType.GEOJSON.name, vlayer)
        group_name = catalog_hrn.split(":")[-1]
        LayerPostProcessor.set_group_name(group_name, vlayer)

        # TODO: handle carto layers, line and polygon
        output = self.Output(
            OUTPUT=vlayer.id(),
            LAYER_ID=[vlayer.id()],
            EXTENT=bbox,
            DEBUG=filename,
            FEAT_CNT=feat_cnt,
        )._asdict()
        output["success"] = True
        return output

    def convert_blob_to_file(self, parsed_blobs: list, filename: str, feedback):
        feedback.pushInfo(filename)
        partitions = list()
        features: Dict = None
        feat_cnt = 0
        for part, feat in parsed_blobs:
            partitions.append(part["id"])
            feat_cnt += len(feat)
            if not features:
                features = feat
            else:
                features["features"].extend(feat["features"])
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(features, f, ensure_ascii=False)
        feedback.pushInfo(str(partitions))
        feedback.pushInfo(str(feat_cnt))
        return feat_cnt

    def postProcessAlgorithm(
        self, context: QgsProcessingContext, feedback: QgsProcessingFeedback
    ) -> Dict[str, Any]:
        for vlayer_id, _details in context.layersToLoadOnCompletion().items():
            vlayer = context.getMapLayer(vlayer_id)
            LayerPostProcessor.update_layer(vlayer)
            LayerPostProcessor.update_style(vlayer)
        return {}
