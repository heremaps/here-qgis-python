###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import json
from typing import Dict, List

import geopandas as gpd
from shapely.geometry import (
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)
from typing_extensions import deprecated

from here_qgis.helper_functions import EMPTY_STRING, is_json_string, remove_dot_number


@deprecated("use NewFlatten instead")
class Flatten:
    def __init__(
        self,
        filename: str = "",
        types_filename: str = "",
        filename_csv: str = "",
    ):
        """
        Creates Flatten object

        # Parameters:
        filename str: Name of input file
        types_filename str: Name of helper json file with types
        filename_csv str: Output filename
        """
        self.types = dict()
        if filename != "":
            self.filename = filename
            if ".geojson" in self.filename:
                with open(self.filename, "r", encoding="utf-8") as f:
                    self.feat = json.load(f)
            elif ".gpkg" in self.filename:
                temp_gdf = gpd.read_file(self.filename)
                self.feat = temp_gdf.to_geo_dict()

                for feature in self.feat["features"]:
                    for key, val in feature["properties"].items():
                        if is_json_string(val):
                            feature["properties"][key] = json.loads(val)
        if types_filename != "":
            if types_filename[len(types_filename) - 4 :] != "json":
                raise Exception("Types filename must be JSON")
            self.types_filename = types_filename
        else:
            self.types_filename = None
        if filename_csv != "":
            self.filename_csv = filename_csv

    # this is original library function with my edits. I get rid of $type
    # only flatten() function is used in flatten_amd_unflatten.py
    def _object_to_rows(self, obj, prefix=None):
        rows = []
        dot_prefix = prefix and (prefix + ".") or ""
        if isinstance(obj, dict):
            if not obj:
                rows.append(((prefix or ""), "{}"))
            else:
                for key, item in obj.items():
                    rows.extend(self._object_to_rows(item, prefix=dot_prefix + key))
        elif isinstance(obj, (list, tuple)):
            if len(obj) == 0:
                rows.append(((prefix or ""), "[]"))
            for i, item in enumerate(obj):
                rows.extend(
                    self._object_to_rows(item, prefix=dot_prefix + "{}".format(i))
                )
        elif obj is None:
            rows.append(((prefix or ""), "None"))
        else:
            if prefix != "geometry":
                rows.append(((prefix or ""), obj))
                prefix = remove_dot_number(prefix)
                if prefix not in self.types:
                    if isinstance(obj, int):
                        self.types[prefix] = "int"
                    elif isinstance(obj, float):
                        self.types[prefix] = "float"
        return rows

    def flatten(self, obj) -> dict:
        """Takes feature (dictionary) and returns flatten dictionary"""
        if not isinstance(obj, dict):
            raise TypeError("Expected dict, got {}".format(type(obj)))
        return dict(self._object_to_rows(obj))

    def flatten_features(self, features) -> List[Dict]:
        """Takes list of features (dictionaries) and
        returns list of dictionaries (each dictionary for one feature)
        """
        flatten_features = []
        for f in features:
            geometry = None
            if "geometry" in f:
                geometry = f["geometry"]
                del f["geometry"]
            flat = self.flatten(f)
            if geometry:
                flat["geometry"] = geometry
            flatten_features.append(flat)
        return flatten_features

    def flatten_feature_collection(self, feature_col) -> List[Dict]:
        """Takes FeatureCollection and returns list of
        dictionaries (each dictionary for one feature).
        Returns list of dictionaries that are compatible with geopandas
        """
        features = feature_col["features"]
        return self.flatten_features(features)

    def flatten_to_df_dict(self, flatten: List[Dict]) -> dict:
        """Takes list of features (dictionaries) and returns dictionary
        with values that are arrays (something like `zip` function)
        """
        new_dict = {}
        none_array = []
        feat_num = 0
        int_keys = []

        for f in flatten:
            for key in f.keys():
                if "geometry" == key:
                    continue

                # if this is a new column,
                # fill it with None so the number of rows would be correct
                if key not in new_dict.keys():
                    if isinstance(f[key], int):
                        int_keys.append(key)
                    new_dict[key] = none_array.copy()

                new_dict[key].append(f[key])

            feat_num += 1
            none_array.append(None)
            # check if last added feature has some missing properties
            for k in new_dict.keys():
                if len(new_dict[k]) < feat_num:
                    new_dict[k].append(None)

        return new_dict

    def process_multipolygon_coords(self, coordinates):
        new_coordinates = []
        for polygon in coordinates:
            outer_ring = polygon[0]
            holes = polygon[1:]
            new_coordinates.append((outer_ring, holes))
        return new_coordinates

    def _choose_geometry(self, geom_type: str, coordinates):
        if geom_type == "Point":
            return Point(coordinates)
        elif geom_type == "LineString":
            return LineString(coordinates)
        elif geom_type == "Polygon":
            return Polygon(coordinates)
        elif geom_type == "MultiPolygon":
            # coordinates = self.process_multipolygon_coords(coordinates) # For macOS
            return MultiPolygon(coordinates)
        elif geom_type == "MultiLineString":
            return MultiLineString(coordinates)
        elif geom_type == "MultiPoint":
            return MultiPoint(coordinates)
        return None

    def get_geometries(self, feat_coll):
        geometries = []
        features = feat_coll["features"]
        for f in features:
            geometry = None
            if "geometry" in f:
                geom = f["geometry"]
                geom_type = geom.get("type")
                geometry = self._choose_geometry(geom_type, geom["coordinates"])

            geometries.append(geometry)
        return geometries

    def process_flatten(self):
        """Flattens feature to `GeoDataFrame` and save to .csv file.
        Additionaly, if proper constructor parameter was passed,
        creates file with types
        """
        gdf = self.flatten_features_2_gdf()

        if self.types_filename is not None:
            with open(self.types_filename, "w", encoding="utf-8") as f:
                json.dump(self.types, f, ensure_ascii=False)

        gdf.to_csv(self.filename_csv, index=False, encoding="utf-8")

    def flatten_features_2_gdf(self) -> gpd.GeoDataFrame:
        """Flatten features to GeoDataFrame"""
        geometry = self.get_geometries(self.feat)
        features = self.flatten_to_df_dict(self.flatten_feature_collection(self.feat))
        gdf = gpd.GeoDataFrame(features, geometry=geometry)
        gdf = gdf.replace("", EMPTY_STRING)

        return gdf
