###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from typing import List

from qgis.core import QgsFeature

# from here_qgis.flatten.flatten import Flatten
from here_qgis.flatten.new_flatten import NewFlatten

from .geojson_to_qgis import GeoJSONToQgis
from .qgis_to_geojson import QgisFeaturesToGeoJSON


class FlattenQgs(NewFlatten):
    """Class flattens QgsFeature into another QgsFeature.

    (QgsFeature -> GeoJSON -> QgsFeature)
    """

    def __init__(self, features: List[QgsFeature]):
        self.features = features
        super().__init__()

    def flatten_on_the_fly(self) -> tuple[list, list]:
        """Returns list of QgsFeature and QgsFields"""
        qgis_2_geojson_obj = QgisFeaturesToGeoJSON(self.features)
        qgs_feature_ids = [f.id() for f in self.features]
        geojson = qgis_2_geojson_obj.list_of_qgis_features_2_feature_coll()

        geojson = self._flatten_geojson_data(geojson)
        geojson_2_qgis_obj = GeoJSONToQgis(geojson, qgs_feature_ids)
        qgis_features = geojson_2_qgis_obj.feature_coll_2_qgis_features()
        qgis_fields = geojson_2_qgis_obj.get_fields()

        return qgis_features, qgis_fields

    def _flatten_geojson_data(self, geojson: dict) -> dict:
        features = self.flatten_feature_collection(geojson)
        new_features = {}
        new_features["type"] = "FeatureCollection"
        new_features["features"] = []

        for feature in features:
            new_feature = {
                "properties": {
                    k: v
                    for k, v in feature.items()
                    if k
                    not in [
                        "geometry",
                        "type",
                    ]  # should momType be in this properties dict ?
                },
                "type": feature["type"],
            }
            if "geometry" in feature:
                new_feature["geometry"] = feature["geometry"]
            new_features["features"].append(new_feature)
        return new_features
