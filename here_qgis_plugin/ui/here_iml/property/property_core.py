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
from datetime import datetime


# TODO: rename to load_property_mapping_from_file, or move to class PropertyMapping
def load_config_from_file(file_path):
    """
    Load and validate field mappings from a JSON file.
    Expected format:
    {
        "title": str,
        "description": str,
        "layers": {
            "layer": {
                "field_name": {
                    "new_name": str,
                    "checked": bool
                }
            }
        }
    }
    """
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Top-level JSON structure must be a dictionary.")

    if "title" not in data or not isinstance(data["title"], str):
        raise ValueError("Missing or invalid 'title' key in the config.")

    if "description" not in data or not isinstance(data["description"], str):
        raise ValueError("Missing or invalid 'description' key in the config.")

    if "layers" not in data or not isinstance(data["layers"], dict):
        raise ValueError("Missing or invalid 'layers' key in the config.")

    layers = data["layers"]

    if not isinstance(layers, dict):
        raise ValueError("'layers' must be a dictionary.")

    for layer, fields in layers.items():
        if not isinstance(fields, dict):
            raise ValueError(f"Each layer ('{layer}') must map to a dictionary.")

        for field_name, field_info in fields.items():
            if not isinstance(field_info, dict):
                raise ValueError(
                    f"Field '{field_name}' in '{layer}' must be a dictionary."
                )

            if "new_name" not in field_info or "checked" not in field_info:
                raise ValueError(
                    f"Field '{field_name}' in '{layer}' must contain 'new_name' and"
                    " 'checked' keys."
                )

            if not isinstance(field_info["new_name"], str):
                raise ValueError(
                    f"'new_name' for field '{field_name}' in '{layer}' must be a"
                    " string."
                )

            if not isinstance(field_info["checked"], bool):
                raise ValueError(
                    f"'checked' for field '{field_name}' in '{layer}' must be a"
                    " boolean."
                )

    return data["layers"]


# TODO: rename to update_property_mapping_file
def update_config_file(file_path, layer_name, items):
    """
    Update the JSON config file with new field mappings.

    :param file_path: Path to the JSON config file.
    :param layer_name: The name of the layer to update.
    :param items: A list of (original_name, new_name, checked) tuples.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            existing_config = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        existing_config = {"title": "", "description": "", "layers": {}}

    if "layers" not in existing_config:
        existing_config["layers"] = {}

    existing_config["layers"][layer_name] = {}
    for original_name, new_name, checked in items:
        if checked or new_name:
            existing_config["layers"][layer_name][original_name] = {
                "new_name": new_name,
                "checked": checked,
            }

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(existing_config, file, ensure_ascii=False, indent=4)


# TODO: rename to create_empty_property_mapping_file
def create_empty_config_file(plugin_dir, save_path_callback):
    """Create and save an empty config JSON file."""
    empty_config = {
        "title": "",
        "description": "",
        "layers": {
            "address": {},
            "building": {},
            "admin": {},
            "carto": {},
            "topology": {},
            "place": {},
            "relation": {},
        },
    }
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"config_{date_str}.json"
    config_path = os.path.join(plugin_dir, file_name)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(empty_config, f, ensure_ascii=False, indent=4)

    save_path_callback(config_path)
    return config_path
