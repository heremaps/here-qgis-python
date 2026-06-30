###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import json
import os

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_preset_titles(directory_path, title_prefix=""):
    """
    Returns a dictionary mapping JSON preset filenames to their 'title' value.
    """
    titles = {}
    if not os.path.isdir(directory_path):
        return titles

    for filename in os.listdir(directory_path):
        if filename.startswith("Preset") and filename.endswith(".json"):
            full_path = os.path.join(directory_path, filename)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                titles[filename] = title_prefix + data.get("title", "")
            except Exception:
                titles[filename] = ""
    return titles


def get_preset_titles_recursive(directory_path):
    """
    Scan preset files recursively in `directory_path`.
    Returns a dictionary mapping JSON preset filenames to their 'title' value.
    """
    titles = get_preset_titles(directory_path)

    for dir_name in os.listdir(directory_path):
        dir_path = os.path.join(directory_path, dir_name)
        if os.path.isdir(dir_path):
            titles.update(get_preset_titles(dir_path, "dev : "))
    return titles


def get_preset_dir():
    return os.path.abspath(os.path.join(MODULE_DIR, "../../../mapping_preset"))


def get_preset_path(filename: str):
    return os.path.join(get_preset_dir(), filename)
