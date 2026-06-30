# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import base64
import json
import re
from typing import Tuple

EMPTY_FILE = "EMPTY_FILE"  # EMPTY_FILE is deprecated
CLICK_KEEP_UNAVAILABLE_LAYERS = "CLICK_KEEP_UNAVAILABLE_LAYERS"
EMPTY_STRING = "EMPTY_STRING"
WHOLE_LAYER = "WHOLE_LAYER"
ON_THE_FLY = "ON_THE_FLY"


def try_parse_json_string(v):
    """
    Try parse json string. On success returns parsed object, on failure returns input.
    """
    if isinstance(v, str) and (v == "[]" or v == "{}"):
        return v  # TODO remove if
    if isinstance(v, str) and ("{" in v or "[" in v):
        try:
            obj = json.loads(v)
            return obj
        except json.JSONDecodeError:
            pass
    return v


def is_json_string(v):
    """
    Checks if string can be parsed into json object
    """
    return v != try_parse_json_string(v)


def try_dumps_json_string(v):
    """
    Try to dump json string if possible, otherwise returns input.

    Function is used because historically QGIS does not handle dict or array type well.
    """
    if isinstance(v, (dict, list, tuple)):
        return json.dumps(v, ensure_ascii=False)
    return v


def xor_encrypt_decrypt(data, key):
    key_len = len(key)
    return bytes(data_byte ^ key[i % key_len] for i, data_byte in enumerate(data))


def deobfuscate_string(obfuscated_string: str, obfuscation_key: str):
    """
    De-obfuscates a text string using Base64 decoding and XOR.

    Args:
        obfuscated_string (str): The obfuscated text string.
        obfuscation_key (str): The same secret string used for XOR.

    Returns:
        str: The original text string.
    """
    scrambled_bytes = base64.b64decode(obfuscated_string.encode("utf-8"))

    obfuscation_key_bytes = obfuscation_key.encode("utf-8")

    text_bytes = xor_encrypt_decrypt(scrambled_bytes, obfuscation_key_bytes)
    return text_bytes.decode("utf-8")


def obfuscate_string(text: str, obfuscation_key: str):
    """
    Obfuscates a text string using XOR and Base64 encoding.

    Args:
        text (str): The raw API key string.
        obfuscation_key (str): A short, secret string to use for XOR.
                                KEEP THIS KEY SECRET!

    Returns:
        str: The obfuscated API key string.
    """
    text_bytes = text.encode("utf-8")
    obfuscation_key_bytes = obfuscation_key.encode("utf-8")

    scrambled_bytes = xor_encrypt_decrypt(text_bytes, obfuscation_key_bytes)

    obfuscated_string = base64.b64encode(scrambled_bytes).decode("utf-8")
    return obfuscated_string


def get_filename_without_ext(filename: str, extension: str) -> str:
    filename = extract_filename(filename)

    name_without_ext = filename[: len(filename) - len(extension) - 1]
    if filename[len(filename) - len(extension) :] != extension:
        return ""
    return name_without_ext


def extract_filename(filename: str) -> str:
    """
    During some QGIS operations the layers source uri may get form:

    'file:///some/path/to/file/filename.ext?someparameter=1&'

    This function extracts the filename

    Function can also be used with .gpkg files, where '|layername=...'
    part is present.

    *param* filename str: e.g.
    file:///some/path/to/file/filename.ext?someparameter=1&

    *return* extracted filename, e.g. some/path/to/file/filename.ext
    """
    if "file:///" in filename:
        filename = filename.replace("file:///", "")
    if "?" in filename:
        filename = filename[: filename.index("?")]
    if "|" in filename:
        filename = filename[: filename.index("|")]
    return filename


def remove_dot_number(path: str):
    reg_array = r"\.\d+"
    start_ends = [(m.start(), m.end()) for m in re.finditer(reg_array, path)]
    changed_length = 0
    for s, e in start_ends:
        path = path[: s - changed_length] + path[e - changed_length :]
        changed_length += e - s
    return path


def get_mom_geojson_from_geojson(geojson: dict) -> Tuple[dict, bool]:
    """Takes GeoJSON which is take from QGIS and converts it
    to GeoJSON complying with MOM.
    Input GeoJSON must have properties.id and properties.momType.
    If those values are not present it is not valid MOM.

    *return* tuple[dict, bool]
    """
    is_valid_mom = True
    for feature in geojson["features"]:
        if "fid" in feature["properties"]:
            del feature["properties"]["fid"]

        # check if "id" and "momType" are at the top level
        if "id" in feature and "momType" in feature:
            is_valid_mom &= True
            continue

        # check for hrn "id" in "properties"
        if "id" in feature["properties"]:
            feature["id"] = feature["properties"]["id"]
            del feature["properties"]["id"]
            is_valid_mom &= True
        else:
            is_valid_mom &= False

        # check for "momType" in "properties"
        if "momType" in feature["properties"]:
            feature["momType"] = feature["properties"]["momType"]
            del feature["properties"]["momType"]
            is_valid_mom &= True
        else:
            is_valid_mom &= False
    return geojson, is_valid_mom


def project_hrn_2_map_project_hrn(project_hrn: str):
    return project_hrn.replace("authorization", "mapmaking-project").replace(
        "project/", ""
    )


def map_project_hrn_2_project_hrn(map_project_hrn: str):
    hrn_prefix, project_id = map_project_hrn.rsplit(":", 1)
    hrn_prefix = hrn_prefix.replace("map-project", "authorization").replace(
        "mapmaking-project", "authorization"
    )
    return f"{hrn_prefix}:project/{project_id}"
