###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import requests
from qgis.core import (
    QgsProcessingFeedback,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterExtent,
    QgsProcessingParameterString,
)

from here_qgis.io.layer_storage import LayerStorage

from .. import config
from ..style_set import StyleConfig
from ..utils.dependencies import install_packages
from .file_type import FileType
from .get_and_load import GetAndLoad
from .here_processing_base import HereProcessingAlgorithm, HereProcessingException

DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
DEFAULT_OVERPASS_QUERY = """[out:json];
(
    way["highway"](
        {{bbox}}
    );
);
out geom;"""


class LoadOSMLayer(HereProcessingAlgorithm):
    @classmethod
    def createInstance(cls):
        return cls()

    def displayName(self) -> str:
        return "OSM: Load OSM to MOM10 Layer"

    def initAlgorithm(self, configuration=None):
        self.addParameter(
            QgsProcessingParameterString(
                "overpass_url",
                "Overpass URL",
                multiLine=False,
                defaultValue=DEFAULT_OVERPASS_URL,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                "overpass_query",
                "Overpass Query",
                multiLine=True,
                defaultValue=DEFAULT_OVERPASS_QUERY,
            )
        )
        self.addParameter(
            QgsProcessingParameterExtent(
                "extent", "Region of interest {{bbox}}", defaultValue=None
            ),
            createOutput=True,
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                "auto_install_deps", "Auto-install dependencies", defaultValue=False
            )
        )

    def get_osm_data(
        self, url, query: str, bbox: dict, feedback: QgsProcessingFeedback
    ) -> dict:
        query = query.replace(
            "{{bbox}}",
            f"""{bbox["y_min"]},{bbox["x_min"]},{bbox["y_max"]},{bbox["x_max"]}""",
        )
        feedback.pushInfo(f"{self.id()} query: \n{query}")
        response = requests.post(
            url,
            data=query.encode("utf-8"),
            headers={
                "content-type": "application/x-www-form-urlencoded; charset=UTF-8"
            },
            timeout=10,  # 10s
        )
        response.raise_for_status()
        return response.json()

    def processAlgorithm(self, parameters, context, feedback: QgsProcessingFeedback):
        auto_install_deps = self.parameterAsBoolean(
            parameters, "auto_install_deps", context
        )

        try:
            from ..mom.osm_to_mom_10 import osm_features_to_mom_feature_collection_dict

        except ImportError as e:
            feedback.reportError(f"{e}")

            if auto_install_deps:
                packages_need_to_install = [
                    "mom_core==10.0.0",
                    "mom_core_geojson==10.0.0",
                ]
                installed = install_packages(packages_need_to_install, isolated=True)

                if not installed:
                    raise HereProcessingException(
                        f"Failed to install {packages_need_to_install}"
                    )

                from ..mom.osm_to_mom_10 import (
                    osm_features_to_mom_feature_collection_dict,
                )
            else:
                raise e

        # fill parameters, for now default values (needed for GetAndLoad)
        parameters["layer_id"] = "Topology"
        parameters["style_set"] = StyleConfig.DEFAULT_STYLE_IDX
        parameters["file_type"] = FileType.GEOPACKAGE.name
        parameters["project_hrn"] = "osm_project"
        parameters["catalog_hrn"] = "osm_catalog"

        overpass_url = self.parameterAsString(parameters, "overpass_url", context)
        overpass_query = self.parameterAsString(parameters, "overpass_query", context)
        bbox = self.get_bbox_from_params(parameters, "extent", context)

        response = self.get_osm_data(overpass_url, overpass_query, bbox, feedback)

        mom_feat_coll = osm_features_to_mom_feature_collection_dict(
            response["elements"]
        )

        imlsave_obj = LayerStorage("topology", "osm", mom_feat_coll, config.TMP_DIR)
        get_and_load = GetAndLoad(bbox, parameters, feedback, context)
        get_and_load.layer_name = "topology"
        get_and_load.group_name = "osm"
        output = get_and_load.load_to_qgis(imlsave_obj, parameters["file_type"])
        output["success"] = True
        return output
