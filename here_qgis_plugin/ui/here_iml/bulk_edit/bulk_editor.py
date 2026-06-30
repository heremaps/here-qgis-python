###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


from qgis.core import NULL, QgsFeature, QgsProject
from qgis.PyQt.QtCore import QMetaType

from here_qgis.flatten.unflatten_helpers import (
    change_dict,
    empty_list_of_nones,
    get_original_key_and_path,
    validate_array,
)
from here_qgis.helper_functions import try_dumps_json_string, try_parse_json_string

from ...here_qgis_processing.flatten_on_fly_processing import flatten_on_fly_processing
from ..base_edit.editor import Editor, EditValueType, JsonLikeString


class BulkEditor(Editor):
    def __init__(self, layer):
        super().__init__(layer)
        self.new_values = {}

    def count_edits(self):
        return len(self.new_values)

    def get_first_feature(self):
        return self.flattened_features[0]

    def get_example_value(self, key):
        return self.get_first_feature().attribute(key)

    def get_flattened_layer(self):
        if self.flattened_layer is None:
            result = flatten_on_fly_processing(layer=self.layer.id())
            self.flattened_layer = QgsProject.instance().mapLayer(
                result["new_layer_id"]
            )
            self.flattened_features = list(self.flattened_layer.getFeatures())
            # copy of original values
            for feature in self.flattened_features:
                self.original_features.append(QgsFeature(feature))
        return self.flattened_layer

    def update_value(self, key: str, value: EditValueType) -> bool:
        """Update value for given key"""
        parsed_value = self.parse_value_to_type(key, str(value))
        if parsed_value is None:
            return False
        self.new_values[key] = parsed_value
        return True

    def reset_value(self, key: str):
        self.new_values.pop(key, "")

    def get_display_value(self, key: str) -> JsonLikeString:
        # can be moved to get_edited_value ?
        if self.layer.selectedFeatureCount() == 1:
            if key not in self.new_values:
                return self.key_value_to_json_like_string(
                    key, self.get_first_feature()[key]
                )
        return self.get_edited_value(key)

    def was_value_edited(self, key: str):
        return self.reverse_lookup_field(key) in self.new_values

    def get_edited_value(self, key: str) -> JsonLikeString:
        if key in self.new_values:
            return self.key_value_to_json_like_string(key, self.new_values[key])
        return ""

    def update_layer(self):
        self.layer.startEditing()

        for key, item in self.new_values.items():
            original_key, path = get_original_key_and_path(key)
            for feature in self.layer.selectedFeatures():
                old_value = try_parse_json_string(feature[original_key])
                if old_value == NULL:
                    continue

                if isinstance(old_value, (dict, list)):
                    new_value = change_dict(old_value, path, item)
                    if not validate_array(new_value, path):
                        raise ValueError(
                            "All elements of array must be None or must have value"
                        )
                    new_value = empty_list_of_nones(new_value)
                else:
                    new_value = item

                field_idx = self.layer.fields().indexOf(original_key)
                self.layer.changeAttributeValue(
                    feature.id(), field_idx, try_dumps_json_string(new_value)
                )
        self.layer.commitChanges()

    def string_field_type(self, original_key) -> str:
        f_type = self.get_field_type(original_key)
        if (
            f_type == QMetaType.Type.Int
            or f_type == QMetaType.Type.UInt
            or f_type == QMetaType.Type.LongLong
        ):
            return "integer"
        elif f_type == QMetaType.Type.Double:
            return "float"
        elif f_type == QMetaType.Type.Bool:
            return "boolean"
        else:
            return "string"
