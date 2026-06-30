###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from typing import Any, Dict, List, Tuple, Union


# TODO: rename to Unflatten after cleanup
class NewUnflatten:
    def unflatten(self, flat_data: List[Tuple[str, Any]]) -> Dict:
        """Unflattens a list of tuples with dotted notation paths
        back into a nested structure.

        Args:
            flat_data: List of tuples containing (path, value) pairs

        Returns:
            Nested dictionary/list structure
        """

        def _convert_lists(obj) -> Union[Dict, List]:
            """Converts dictionary with numeric keys to lists where appropriate."""
            if not isinstance(obj, dict):
                return obj

            if obj and all(k.isdigit() for k in obj):
                return [_convert_lists(obj[str(i)]) for i in range(len(obj))]

            return {k: _convert_lists(v) for k, v in obj.items()}

        result = {}
        for key, value in flat_data:
            current = result
            *path_parts, last = key.split(".")
            for part in path_parts:
                current = current.setdefault(part, {})
            if value == "{}":
                value = {}
            if value == "[]":
                value = []
            current[last] = value

        return _convert_lists(result)

    def align_to_mom(self, f):
        f["type"] = "Feature"
        # in flatten/unflatten on the fly new approach it is not nedded
        # f["properties"]["momType"] = f["momType"]
        # f["properties"]["id"] = f["id"]
        # del f["momType"]
        # del f["id"]
        return f

    def unflattened_feature_to_collection(self, features: List[Dict]) -> Dict:
        """Creates feature collection out of list of features (dictionaries).
        Feature collection has MOM structure.
        """
        for f in features:
            f = self.align_to_mom(f)
        unflatten_dict = dict()
        unflatten_dict["type"] = "FeatureCollection"
        unflatten_dict["features"] = features

        return unflatten_dict
