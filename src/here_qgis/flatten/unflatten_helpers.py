###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import json
from functools import reduce
from typing import Tuple, Union


def get_dict_element_from_path(d: dict, path: list):
    current = d
    for curr_key in path:
        current = current[curr_key]
    return current


def validate_array(new_value: dict, path: list):
    last_path_element = path[-1]
    try:
        int(last_path_element)
        dict_path = path[:-1]
        list_to_check = get_dict_element_from_path(new_value, dict_path)
        not_none_elements = 0
        for el in list_to_check:
            if el != "" and el is not None:
                not_none_elements += 1
        if not_none_elements != 0 and not_none_elements != len(list_to_check):
            return False
    except ValueError:
        pass
    return True


def empty_list_of_nones(obj):
    if not isinstance(obj, list):
        return obj
    all_nones = reduce(lambda acc, x: acc and x is None, obj, True)
    if all_nones:
        return []
    return obj


def change_dict(d: Union[dict, list], path: list, val):
    """Function recursively updates element in dict/list pointed out by `path` list.

    E.g. `change_dict({"a": {"b": {"c": {"d": 22}}}}, ["a", "b", "c", "d"], 55)`
    will result with `{"a": {"b": {"c": {"d": 55}}}}`.

    If reaching to list pass index as string, e.g.
    `change_dict([{"a": 12}, {"a": 22}], ["1", "a"], 55)`
    will result with `[{"a": 12}, {"a": 55}]`.
    """
    next_element = path[0]
    try:
        next_element = int(next_element)
    except ValueError:
        pass
    if len(path) == 1:
        d[next_element] = val
        return d
    d[next_element] = change_dict(d[next_element], path[1:], val)
    return d


def get_original_key_and_path(flat_key: str) -> Tuple[str, list]:
    """Function takes flattened key and returns original key and path to the last
    element as a list.

    E.g. get_original_key_and_path("properties.path.0.some_val.another") would return
    Tuple("path", ["0", "some_val", "another"])
    """
    keys = flat_key.split(".")
    if len(keys) == 1:
        original_key = keys[0]
        json_path = keys
    else:
        original_key = keys[1]
        json_path = keys[2:]
    return original_key, json_path


def parse_json_like_string(v: str):
    if v == "null":
        return None
    try:
        return json.loads(v)
    except json.JSONDecodeError:
        return v


def parse_json_like_text_input(v: str):
    """Conform text input to python data type compatible with json.dumps()"""
    if v.lower() == "true":
        return True
    elif v.lower() == "false":
        return False
    elif v.lower() == "null":
        return None
    else:
        return parse_json_like_string(v)
