###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import json
from urllib.request import urlopen

from qgis.core import QgsProcessingParameterExtent

from here_qgis.io.layer_storage import LayerStorage

from .. import config
from ..config import REPO_DIR
from ..style_set import StyleConfig
from ..utils.dependencies import install_packages
from .file_type import FileType
from .get_and_load import GetAndLoad
from .here_processing_base import HereProcessingAlgorithm, HereProcessingException


class LoadOSMLayer(HereProcessingAlgorithm):
    @classmethod
    def createInstance(cls):
        return cls()

    def displayName(self) -> str:
        return "OSM: Load OSM to IMOM Layer"

    def initAlgorithm(self, configuration=None):
        self.addParameter(
            QgsProcessingParameterExtent(
                "extent", "Region of interest", defaultValue=None
            ),
            createOutput=True,
        )

    def get_osm_data(self, bbox):
        query = f"""[out:json];
            (
                way["highway"](
                    {bbox["y_min"]},{bbox["x_min"]},{bbox["y_max"]},{bbox["x_max"]}
                );
            );
            out geom;
        """
        url = "https://overpass-api.de/api/interpreter"
        query = query.encode("utf-8")
        f = urlopen(url, query)
        read_chunk_size = 4096
        response = f.read(read_chunk_size)
        while True:
            data = f.read(read_chunk_size)
            if len(data) == 0:
                break
            response = response + data
        f.close()
        data = response.decode("utf-8")
        return json.loads(data)

    def processAlgorithm(self, parameters, context, feedback):
        # fill parameters, for now default values (needed for GetAndLoad)
        parameters["layer_id"] = "Topology"
        parameters["style_set"] = StyleConfig.DEFAULT_STYLE_IDX
        parameters["file_type"] = FileType.GEOPACKAGE.name
        parameters["project_hrn"] = "osm_project"
        parameters["catalog_hrn"] = "osm_catalog"

        bbox = self.get_bbox_from_params(parameters, "extent", context)
        response = self.get_osm_data(bbox)
        try:
            from ..mom.osm_to_mom_10 import osm_features_to_mom_feature_collection_dict

        except ImportError as e:
            feedback.reportError(f"{e}")

            for core_dep in ["here_qgis", REPO_DIR]:
                packages_need_to_install = [
                    f"{core_dep}[mom-core-10, mom-internal-8]",
                ]

                installed = install_packages(packages_need_to_install, isolated=True)
                if installed:
                    break

            if not installed:
                raise HereProcessingException(
                    f"Failed to install {packages_need_to_install}"
                )

            from ..mom.osm_to_mom_10 import osm_features_to_mom_feature_collection_dict

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
