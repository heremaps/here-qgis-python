###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import json
from typing import List

from qgis.core import NULL, QgsFeature

from here_qgis.helper_functions import try_parse_json_string


class QgisFeaturesToGeoJSON:
    """Converts QgsFeature to GeoJSON dict."""

    def __init__(self, qgis_features: List[QgsFeature]):
        self.qgis_features = qgis_features

    def qgs_feature_2_dict(self, qgis_feature: QgsFeature) -> dict:
        """Converts QgsFeature to dictionary. It also parses QgsGeometry
        to json structure"""
        feature = dict()
        feature["properties"] = dict()
        feature["type"] = "Feature"

        attributes = qgis_feature.attributeMap()
        for key, value in attributes.items():
            if key == "fid":
                continue
            if value is not None and value != NULL:
                feature["properties"][key] = try_parse_json_string(value)

        if not qgis_feature.geometry().isNull():
            feature["geometry"] = json.loads(qgis_feature.geometry().asJson())
        return feature

    def list_of_qgis_features_2_feature_coll(self) -> dict:
        feature_coll = {}
        feature_coll["type"] = "FeatureCollection"
        feature_coll["features"] = []

        for qgis_feature in self.qgis_features:
            feature_coll["features"].append(self.qgs_feature_2_dict(qgis_feature))

        return feature_coll
