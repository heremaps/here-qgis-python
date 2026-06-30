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
import re
from typing import Dict, List, Optional

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import wkt
from typing_extensions import deprecated

from here_qgis.helper_functions import EMPTY_STRING, remove_dot_number


@deprecated("use NewUnflatten instead")
class Unflatten:
    def __init__(
        self,
        filename: Optional[str] = None,
        types_filename: Optional[str] = None,
        new_filename: Optional[str] = None,
        # gdf=None,
    ):
        """
        Creates Unflatten object

        # Parameters:
        filename str: Name of input file

        types_filename str: Name of helper json file with types

        new_filename str: Output filename

        When *filename* provided *types_filename* must be provided
        (use when unflatten layers with flattened=WHOLE_LAYER metadata).

        When layer has flattened=ON_THE_FLY provide *features*
        and *fields* parameters.

        *new_filename* must always be provided.
        """
        if filename and types_filename and new_filename:
            self.filename = filename
            self.types_filename = types_filename
            self.features = None
            with open(self.types_filename, "r", encoding="utf-8") as f:
                self.types_read = json.load(f)

            self.new_filename = new_filename

    def can_cast(self, val, dest_type):
        try:
            dest_type(val)
            return True
        except ValueError:
            return False

    def get_type(self, path: str):
        if path in self.types_read:
            return self.types_read[path]
        return "str"

    def is_bool(self, value):
        return (
            isinstance(value, str)
            and (value.lower() == "true" or value.lower() == "false")
        ) or isinstance(value, bool)

    def _provide_type(
        self,
        new_key: str,
        value,
        key: str,
        on_the_fly: bool,
    ):
        if isinstance(value, dict):
            return new_key

        if self.is_bool(value):
            new_key += "$bool"
        elif not on_the_fly:
            if self.can_cast(value, int):
                f_type = self.get_type(remove_dot_number(key))
                if f_type != "str":
                    new_key += "$" + f_type
            elif self.can_cast(value, float):
                new_key += "$float"
        else:
            if isinstance(value, int):
                new_key += "$int"
            elif isinstance(value, float):
                new_key += "$float"

        return new_key

    _types_re = re.compile(r".*\$(none|bool|int|float|empty|emptylist)$")
    _int_key_re = re.compile(r"\[(\d+)\]")

    def unflatten_lib(self, data, on_the_fly):
        obj = {}
        for key, value in data.items():
            current = obj
            bits = key.split(".")
            path, lastkey = bits[:-1], bits[-1]
            for bit in path:
                if on_the_fly and not isinstance(current, dict):
                    current = {}
                    current[bit] = {}
                else:
                    current[bit] = current.get(bit) or {}
                current = current[bit]
            # Now deal with $type suffixes:
            if self._types_re.match(lastkey):
                lastkey, lasttype = lastkey.rsplit("$", 2)
                value = {
                    "int": int,
                    "float": float,
                    "empty": lambda v: {},
                    "emptylist": lambda v: [],
                    "bool": lambda v: v.lower() == "true",
                    "none": lambda v: None,
                }.get(lasttype, lambda v: v)(value)
            if value == "{}":
                value = {}
            if value == "[]":
                value = []
            current[lastkey] = value

        # We handle foo.[0].one, foo.[1].two syntax in a second pass,
        # by iterating through our structure looking for dictionaries
        # where all of the keys are stringified integers
        def replace_integer_keyed_dicts_with_lists(obj):
            if isinstance(obj, dict):
                if obj and all(self._int_key_re.match(k) for k in obj):
                    return [
                        i[1]
                        for i in sorted(
                            [
                                (
                                    int(self._int_key_re.match(k).group(1)),
                                    replace_integer_keyed_dicts_with_lists(v),
                                )
                                for k, v in obj.items()
                            ]
                        )
                    ]
                else:
                    return dict(
                        (k, replace_integer_keyed_dicts_with_lists(v))
                        for k, v in obj.items()
                    )
            elif isinstance(obj, list):
                return [replace_integer_keyed_dicts_with_lists(v) for v in obj]
            else:
                return obj

        obj = replace_integer_keyed_dicts_with_lists(obj)
        # Handle root units only, e.g. {'$empty': '{}'}
        if list(obj.keys()) == [""]:
            return list(obj.values())[0]
        return obj

    def unflatten_gdf_2_features(
        self, gdf: gpd.GeoDataFrame, on_the_fly: bool = False
    ) -> List[Dict]:
        """Unflattens GeoDataFrame to list of features (dictionaries)"""
        features = []

        if "momType" in gdf:
            layer = gdf["momType"][0].lower()
        else:
            layer = gdf["properties.momType"][0].lower()

        layer = layer.removeprefix('"').removesuffix('"')
        reg_array = r"\.\d+"
        for _, row in gdf.iterrows():
            curr_feat = {}
            keys = row.keys()

            for key in keys:
                value = row[key]
                # dont use None values
                if on_the_fly and (isinstance(value, str) and value == ""):
                    value = None
                if value is not None:
                    new_key = key
                    # dont add float none values
                    if isinstance(value, float) and (
                        np.isnan(value) or pd.isna(value) or math.isnan(value)
                    ):
                        continue
                    if value == "[]":
                        # curr_feat[PROP + '.' + new_key] = []
                        curr_feat[new_key] = []
                        continue
                    if value == "{}":
                        value = {}

                    # this if is probably not needed while dealing
                    # with geojsons taken directly from platform
                    if value == "NaN":
                        # curr_feat[PROP + '.' + new_key] = value
                        curr_feat[new_key] = value
                        continue

                    if new_key == "geometry":
                        if not on_the_fly:
                            value = wkt.loads(value)
                        geom = json.loads(gpd.GeoSeries(value).to_json())["features"][
                            0
                        ]["geometry"]
                        curr_feat[new_key] = geom
                        continue
                    if new_key == "type":
                        curr_feat[new_key] = value
                        continue

                    start_ends = [
                        (m.start(), m.end()) for m in re.finditer(reg_array, new_key)
                    ]
                    changed_length = 0
                    for s, e in start_ends:
                        new_key = (
                            new_key[: s + 1 + changed_length]
                            + "["
                            + new_key[s + 1 + changed_length : e + changed_length]
                            + "]"
                            + new_key[e + changed_length :]
                        )
                        changed_length += 2

                    new_key = self._provide_type(new_key, value, key, on_the_fly)
                    if on_the_fly:
                        # dont convert ampty dicts to string
                        if isinstance(value, dict) and not value:
                            pass
                        elif value == EMPTY_STRING:
                            value = ""
                        else:
                            value = str(value)
                    curr_feat[new_key] = value

            features.append(self.unflatten_lib(curr_feat, on_the_fly))
        return features

    def align_to_mom(self, f):
        f["type"] = "Feature"
        # in flatten/unflatten on the fly new approach it is not nedded
        # f["properties"]["momType"] = f["momType"]
        # f["properties"]["id"] = f["id"]
        # del f["momType"]
        # del f["id"]
        return f

    def unflattened_feature_to_collection(
        self, features: List[Dict], on_the_fly: bool = False
    ) -> dict:
        """Creates feature collection out of list of features (dictionaries).
        Feature collection has MOM structure.
        """
        if on_the_fly:
            for f in features:
                f = self.align_to_mom(f)
        unflatten_dict = dict()
        unflatten_dict["type"] = "FeatureCollection"
        unflatten_dict["features"] = features

        return unflatten_dict

    def unflatten_gdf_2_file(self, on_the_fly):
        """Unflattens GeoDataFrame and saves to the .geojson file.

        1st step in on the fly

        2nd step in not on the fly
        """
        features = self.unflatten_gdf_2_features(self.gdf, on_the_fly)
        feature_collection = self.unflattened_feature_to_collection(
            features, on_the_fly
        )

        with open(self.new_filename, "w", encoding="utf-8") as f:
            json.dump(feature_collection, f, ensure_ascii=False)

    def process_unflatten(self):
        """Unflattens table from .csv file to .geojson file. NOT on the fly approach"""
        self.gdf = gpd.read_file(self.filename, encoding="utf-8")
        self.gdf = self.gdf.replace("", None)
        self.gdf = self.gdf.replace("None", None)
        self.gdf = self.gdf.replace("NULL", None)
        self.gdf = self.gdf.replace(EMPTY_STRING, "")
        self.unflatten_gdf_2_file(False)

    def replace_array_keys(self, key):
        reg_array = r"\.\d+"
        start_ends = [(m.start(), m.end()) for m in re.finditer(reg_array, key)]
        changed_length = 0
        for s, e in start_ends:
            key = (
                key[: s + 1 + changed_length]
                + "["
                + key[s + 1 + changed_length : e + changed_length]
                + "]"
                + key[e + changed_length :]
            )
            changed_length += 2
        return key
