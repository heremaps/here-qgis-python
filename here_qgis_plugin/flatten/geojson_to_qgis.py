###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import json
from typing import List, Optional

from osgeo import ogr
from qgis.core import QgsFeature, QgsField, QgsFields, QgsGeometry, QgsJsonUtils
from qgis.PyQt.QtCore import QVariant


class GeoJSONToQgis:
    """Converts list of dictionaries (features) to list of QgsFeature.
    Dictionaries should have geometries (GeoJSON).
    `qgs_feature_ids` can be provided optionally for consistency

    Use `list_of_features_2_qgis_features()` function to convert.

    Use `get_fields()` function to get QgsFields`
    """

    def __init__(self, feature_coll: dict, qgs_feature_ids: Optional[List[int]] = None):
        self.features = feature_coll["features"]
        self.all_fields = QgsFields()
        self.columns = self._set_of_columns_names_and_types()
        self.qgs_feature_ids = (
            qgs_feature_ids
            if qgs_feature_ids
            else [i + 1 for i in range(len(self.features))]
        )

    def _get_type(self, value):
        """Gets value and returns QVariant type"""
        if isinstance(value, bool):
            return QVariant.Bool
        if isinstance(value, int):
            return QVariant.LongLong
        if isinstance(value, float):
            return QVariant.Double
        return QVariant.String

    def _set_of_columns_names_and_types(self) -> dict:
        """Returns dictionary of all keys with corresponding type
        # Returns
        columns `dict`: Set of all columns
        """
        columns = dict()
        # TODO: verify this with gpkg layer
        columns["fid"] = QVariant.LongLong
        for feature in self.features:
            for key, value in feature["properties"].items():
                # if key == "geometry":
                #     continue
                if key not in columns:
                    type = self._get_type(value)
                    columns[key] = type
                    self.all_fields.append(QgsField(key, type))
        return columns

    def dict_2_qgs_feature(self, feature: dict, fid: int) -> QgsFeature:
        """Creates `QgsFeature` out of dictionary (feature)
        # Parameters
        feature `dict`: Feature to save as `QgsFeature`

        fid `int`: ID of feature
        # Returns
        `QgsFeature`
        """
        feature_keys = feature["properties"].keys()

        qgis_feature = QgsFeature(self.all_fields, fid)
        if "geometry" in feature:
            qgis_feature.setGeometry(
                self.qgs_geometry_from_geojson(feature["geometry"])
            )
        for column in self.columns.keys():
            # TODO: verify this
            # if column == "fid":
            #     qgis_feature.setAttribute(column, fid)
            #     continue
            if column in feature_keys:
                qgis_feature.setAttribute(column, feature["properties"][column])

        return qgis_feature

    def feature_coll_2_qgis_features(self) -> List[QgsFeature]:
        """Converts list of dictionaries (features) to list of QgsFeature"""
        qgis_features = []

        for fid, feature in zip(self.qgs_feature_ids, self.features):
            qgis_features.append(self.dict_2_qgs_feature(feature, fid))
        return qgis_features

    def get_fields(self):
        return self.all_fields

    @staticmethod
    def qgs_geometry_from_geojson(geometry_dict: dict):
        s = json.dumps(geometry_dict)
        if hasattr(QgsJsonUtils, "geometryFromGeoJson"):
            return QgsJsonUtils.geometryFromGeoJson(s)
        else:
            return QgsGeometry.fromWkt(ogr.CreateGeometryFromJson(s).ExportToWkt())
