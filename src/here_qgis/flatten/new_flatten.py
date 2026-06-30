###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from typing import Any, Dict, List, Tuple, Union


# TODO: rename to Flatten after cleanup
class NewFlatten:
    def _core_flatten(
        self, data: Union[Dict, List, Any], prefix: str = ""
    ) -> List[Tuple[str, Any]]:
        """Flattens a nested dictionary or list into a list of tuples
        with dotted notation paths.

        Args:
            data: Dictionary or list to flatten
            prefix: Current path prefix for nested structures

        Returns:
            List of tuples containing (path, value) pairs
        """
        flattened = []

        if isinstance(data, dict) and data:
            for key, value in data.items():
                new_key = f"{prefix}.{key}" if prefix else key
                flattened.extend(self._core_flatten(value, new_key))
        elif isinstance(data, (list, tuple)) and data:
            for idx, val in enumerate(data):
                flattened.extend(self._core_flatten(val, f"{prefix}.{idx}"))
        elif data == {}:
            flattened.append(((prefix or ""), "{}"))
        elif data == []:
            flattened.append(((prefix or ""), "[]"))
        else:
            flattened.append((prefix, data))

        return flattened

    def flatten(self, obj) -> dict:
        """Takes feature (dictionary) and returns flatten dictionary"""
        if not isinstance(obj, dict):
            raise TypeError("Expected dict, got {}".format(type(obj)))
        return dict(self._core_flatten(obj))

    def flatten_features(self, features: List[Dict]) -> List[Dict]:
        """Takes list of features (dictionaries) and
        returns list of dictionaries (each dictionary for one feature)
        """
        flatten_features = []
        for f in features:
            geometry = f.pop("geometry", None)
            flat = self.flatten(f)
            if geometry:
                flat["geometry"] = geometry
            flatten_features.append(flat)
        return flatten_features

    def flatten_feature_collection(self, feature_col: Dict) -> List[Dict]:
        """Takes FeatureCollection and returns list of
        dictionaries (each dictionary for one feature).
        Returns list of dictionaries that are compatible with geopandas
        """
        features = feature_col["features"]
        return self.flatten_features(features)
