###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import json
import math
from typing import List

from qgis.core import QgsFeature

# from here_qgis.flatten.unflatten import Unflatten
from here_qgis.flatten.new_unflatten import NewUnflatten

from .qgis_to_geojson import QgisFeaturesToGeoJSON


class UnflattenQGS(NewUnflatten):
    """Class unflattens QgsFeature into GeoJSON dictionary and save to file

    (QgsFeature -> GeoJSON dict)
    """

    def __init__(self, qgis_features: List[QgsFeature]):
        self.qgis_features = qgis_features
        super().__init__()

    def unflatten_to_features(self) -> List[dict]:
        qgis_to_dict_obj = QgisFeaturesToGeoJSON(self.qgis_features)
        feature_coll = qgis_to_dict_obj.list_of_qgis_features_2_feature_coll()
        features = feature_coll["features"]
        unflattened_features = []
        # TODO: dont use new_feature
        for feature in features:
            new_feature = {}
            for key, value in feature["properties"].items():
                # if key == "geometry":
                #     continue
                if value is not None and isinstance(value, float) and math.isnan(value):
                    value = "NaN"
                # new_key = self.replace_array_keys(key)
                new_feature[key] = value
            new_feature = self.unflatten(new_feature.items())
            if "geometry" in feature:
                new_feature["geometry"] = feature["geometry"]
            self.align_to_mom(new_feature)
            unflattened_features.append(new_feature)
        return unflattened_features

    def unflatten_to_file(self, filename: str):
        if not filename:
            raise ValueError(f"invalid filename: {filename}")

        feature_collection = self.unflattened_feature_to_collection(
            self.unflatten_to_features()
        )

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(feature_collection, f, ensure_ascii=False)
