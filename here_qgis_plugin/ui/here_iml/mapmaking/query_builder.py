###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from typing import List, Tuple

from here_qgis.helper_functions import try_parse_json_string

NON_ARRAY_FILTER_OPTIONS = ["<=", ">=", "=", "<", ">"]
ARRAY_FILTER_OPTION = ["=cs="]


class QueryBuilder:
    """Class for building query for filtering data in IML API
    (https://interactive.data.api.platform.here.com/openapi/?url=/interactive/v1/static/openapi/interactive-map-api-viewer-experimental.yaml#/Read%20Features/getFeaturesByTile).
    Usage:
    `builder = QueryBuilder()`
    `builder.add_filter("p.accessCharacteristics.0.emergencyVehicle", "false")`

    `builder.add_filter("p.speedLimit.0.valueKph", "30")`

    It's possible to add whole query as string:

    `builder.add_query(
    'p.accessCharacteristics=cs={"auto": true}&
    p.accessCharacteristics=cs={"bus": false}"
    )`

    `query = builder.build_query()`

    string with query in `query` variable
    ### Limitations
    IML API allows to combine logical `AND` and `OR`. That class only allows for `AND`
    """

    def __init__(self):
        self.filters = {}

    def add_filter(self, key: str, value: Tuple[str, str]):
        """
        Adding filter to the builder.

        As the IML API documentation says, properties that are not inside "properties"
        dictionary should start with "p.", otherwise with "f.".
        There are three properties outside "properties" dict allowed:
        `f.id`, `f.createdAt`, `f.updatedAt`. It is not verified in that class,
        but potentially might raise errors on the server side.

        :param key: Field name. If inside "properties" dictionary, should start with
            "p.", e.g. "p.speedLimit.0.valueKph". Otherwise it should start with
            "f.", e.g. "f.id".
            Note that when calling this function the "f." should be omitted,
            so it should be add_filter("id").
            "p." must not be omitted.
        :type key: str
        :param value: Value of the filter. First element is filter option,
        second is a value
        :type value: Tuple[str, str]
        """
        self.filters[key] = value

    def remove_filter(self, key: str):
        self.filters.pop(key, "")

    def get_value(self, key: str) -> Tuple[str, str]:
        return self.filters.get(key, ("", ""))

    def clear(self):
        self.filters = {}

    def field_in_query(self, key: str):
        return key in self.filters

    def validate_query(self, entry: str) -> Tuple[str, Tuple[str, str]]:
        """Validates given entry in query. Checks for different filter operators,
        otherwise raises ValueError.
        # Params
        entry `str`: one of query entries

        # Returns
        `Tuple[str, Tuple[str, str]]`: (key, (filter, value)) pair

        # Raises
        `ValueError`
        """
        if ARRAY_FILTER_OPTION[0] in entry:
            key_val = entry.split(ARRAY_FILTER_OPTION[0])
            key = key_val[0]
            dict_val = list(try_parse_json_string(key_val[1]).items())[0]
            if key[0] != "p":
                key = key[1:]
            key += ".0." + str(dict_val[0])
            val = dict_val[1]
            filter_op = ARRAY_FILTER_OPTION[0]
        else:
            broken = False
            for option in NON_ARRAY_FILTER_OPTIONS:
                key_val = entry.split(option)
                if len(key_val) == 2:
                    filter_op = option
                    key = key_val[0]
                    val = key_val[1]
                    if key[0] != "p":
                        key = key[2:]
                    broken = True
                    break
            if not broken:
                raise ValueError("Wrong query format:", entry)

        if isinstance(val, bool):
            val = str(val).lower()
        else:
            val = str(val)
        return key, (filter_op, val)

    def add_query(self, query: str):
        """Adds query to filters (check class docstring for example)"""
        if query:
            entries = query.split("&")
            try:
                for entry in entries:
                    key, val = self.validate_query(entry)
                    self.filters[key] = val
            except Exception as e:
                # TODO: how to handle that error?
                print(e)

    def _is_array(self, key: str) -> Tuple[bool, List[str], str]:
        """Based on `key` decides whether its part of array or not.
        # Return
        `Tuple[bool, List[str], str]` -
        (
            array or not;
            path for the property;
            last part of path for arrays,
            empty otherwise
        )
        """
        path = key.split(".")
        if len(path) == 1:
            return False, path, ""
        if len(path) == 2 and (path[0] == "p" or path[0] == "f"):
            return False, [path[1]], ""
        try:
            int(path[-2])
            return True, path[1:-2], path[-1]
        except ValueError:
            return False, path, ""

    def _build_query_from_key(self, key: str, value: Tuple[str, str]) -> str:
        """Builds query from given (key, value) pair.
        Operator passed in the tuple is used to build a query.
        # Params
        key `str`: key of the filter, e.g.
        p.accessCharacteristics.0.emergencyVehicle, f.id

        `value `Tuple[str, str]`: (filter option, value) of the filter
        ### Returns
        `str`
        """
        starts_with = "p." if "p." == key[:2] else "f."

        is_arr, path, last = self._is_array(key)
        new_path = starts_with + ".".join(path[0:])

        if is_arr:
            query = new_path + '=cs={"' + last + f'": {value[1]}' + "}"
        else:
            query = new_path + value[0] + value[1]
        return query

    def build_query(self):
        query = ""
        for key, value in self.filters.items():
            # TODO: now there is AND only. maybe add OR
            query += self._build_query_from_key(key, value) + "&"
        return query

    def get_all_operators(self, long_key):
        if ".0." in long_key:
            return ARRAY_FILTER_OPTION
        else:
            return NON_ARRAY_FILTER_OPTIONS
