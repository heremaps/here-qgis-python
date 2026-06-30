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
from abc import abstractmethod
from typing import Literal, Union

from qgis.core import QgsFeature, QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import QMetaType
from qgis.utils import iface

from ....processing_toolbox.get_and_load import DEFAULT_IML_LAYERS as LAYERS
from ..property.property_core import load_config_from_file

EditValueType = Union[bool, int, float, str]
JsonLikeString = Union[str, Literal["true", "false", "null"]]


class Editor:
    def __init__(self, layer: Union[QgsVectorLayer, None] = None):
        self.layer = layer
        self.flattened_layer = None
        self.flattened_features = []
        self.original_features = []
        self.rename_field_mapping = {}

    @abstractmethod
    def get_flattened_layer(self):
        raise NotImplementedError()

    @abstractmethod
    def update_layer(self):
        raise NotImplementedError()

    def get_renamed_field_mapping(self, preset_path: str = ""):
        matched_layer_keyword = next(
            (
                layer_type
                for layer_type in LAYERS
                if layer_type in self.flattened_layer.name().lower()
            ),
            "",
        )

        if not preset_path or not os.path.exists(preset_path):
            matched_from_config_data = {}
        else:
            # Config exists: load and apply mapping
            validate_config_data = load_config_from_file(preset_path)
            matched_from_config_data = validate_config_data.get(
                matched_layer_keyword, {}
            )

        if not matched_from_config_data:
            self.rename_field_mapping = {
                field.name(): field.name() for field in self.flattened_layer.fields()
            }
        else:
            self.rename_field_mapping = {
                field: details.get("new_name", field) or field
                for field, details in matched_from_config_data.items()
                if details.get("checked", False)
            }

        return self.rename_field_mapping

    def reverse_lookup_field(self, renamed_field: str):
        for original, renamed in self.rename_field_mapping.items():
            if renamed == renamed_field:
                return original
        return None

    def set_active_layer(self, layer: QgsVectorLayer):
        if iface:
            iface.setActiveLayer(layer)

    def _remove_layer(self, layer: Union[QgsVectorLayer, None]):
        if layer:
            QgsProject.instance().removeMapLayer(layer.id())

    def remove_flattened_layer(self):
        if self.flattened_layer:
            self._remove_layer(self.flattened_layer)
            self.flattened_layer = None
        self.set_active_layer(self.layer)

    def get_field_type(self, name: str):
        fields = self.flattened_layer.fields()
        return fields.at(fields.indexFromName(name)).type()

    def get_feature_field_type(self, feature: QgsFeature, key: str):
        fields = feature.fields()
        return fields.at(fields.indexFromName(key)).type()

    def parse_value_to_type(self, key: str, value: JsonLikeString):
        """Parse json like string `value` to type of `key` of flattened layer
        by getting its QgsField type
        """
        try:
            field_type = self.get_field_type(key)
            if field_type == QMetaType.Type.Double:
                return float(value)
            if (
                field_type == QMetaType.Type.Int
                or field_type == QMetaType.Type.UInt
                or field_type == QMetaType.Type.LongLong
            ):
                if "." in value:
                    raise ValueError()
                return int(value)
            if field_type == QMetaType.Type.Bool:
                if value.lower() not in ["true", "false"]:
                    raise ValueError()
                return value.lower() == "true"
            return value
        except ValueError:
            return None

    def key_value_to_json_like_string(
        self, key: str, value: EditValueType
    ) -> JsonLikeString:
        """Convert key value of flattened layer to json like string.
        Inverse of `parse_value_to_type`
        """
        if value is None:
            return "null"
        field_type = self.get_field_type(key)
        if field_type == QMetaType.Type.Bool:
            return "true" if value else "false"
        return str(value)

    # unused
    def json_like_string(self, value) -> JsonLikeString:
        json_like_val = json.dumps(value)
        # prevent from "" in 'true' strings, e.g. "BOTH" -> BOTH
        return json_like_val[1:-1] if json_like_val.startswith('"') else json_like_val
