###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


from qgis.core import (
    QgsExpression,
    QgsFeature,
    QgsFeatureRequest,
    QgsProject,
    QgsVectorLayer,
)

from here_qgis.helper_functions import try_dumps_json_string

from ...here_qgis_processing.flatten_on_fly_processing import flatten_on_fly_processing
from ...here_qgis_processing.unflatten_on_fly_processing import (
    unflatten_on_fly_processing,
)
from ..base_edit.editor import Editor

# Todo:
# Edited_feature count (test case)
# Get the edited feature (logic)
# Get unflattened layer from the edited feature (processing function)


class IdsAndColumns:
    """Class to store qgis_id, here_id and edited columns names
    of the feature. If `self.edited_columns` set is empty it means
    that feature was not edited. Otherwise names in that set says which
    columns were edited
    """

    def __init__(self, qgis_id: int, here_id: str):
        self.qgis_id = qgis_id
        self.here_id = here_id
        self.edited_fields = set()

    def add_column(self, col_name):
        self.edited_fields.add(col_name)

    def remove_column(self, col_name):
        self.edited_fields.discard(col_name)

    def __repr__(self):
        return f"IdsAndColumns(fid={self.qgis_id}, id={self.here_id})"


class LayerEditor(Editor):
    def __init__(self, layer: QgsVectorLayer):
        """
        Class works on the flattened layer, which is created from the
        original layer with the `get_flattened_layer()` function.
        Unflattened layer is
        used after all the work is done (in `update_layer()` function).

        `self.layer` - original layer.

        `self.flattened_layer` - flattened original layer

        `self.flattened_features` - list of flattened features.
        Those features are edited.

        `self.original_features` - list of flattened features.
        Those features are not edited - they have original values.

        `self.ids_and_columns` is a list of IdsAndColumns objects

        `self.current_index` - index of currently edited feature.
        It can be used for access to `flattened_features`, `original_features`,
        `ids_and_columns`.

        `len(flattened_features)` == `len(original_features)`

        `self.unflattened_layer` - unflattend layer.
        """
        super().__init__(layer)
        self.ids_and_columns = [
            IdsAndColumns(feature.id(), feature["id"])
            for feature in self.layer.selectedFeatures()
        ]
        self.unflattened_layer = None
        self.current_index = 0
        self.max_current_index = -1

    def get_feature_count(self):
        return len(self.flattened_features)

    @staticmethod
    def get_mom_id(feature):
        """Get MOM id from QgsFeature (normal layer or flattened layer)"""
        value = ""
        attributes = feature.attributeMap()
        for key in ["id", "properties.id"]:
            if key in attributes:
                value = attributes[key]
                break
        return value

    def get_feature_labels(self):
        return [
            "Feature {i} | {mom_id}".format(i=i + 1, mom_id=self.get_mom_id(feat))
            for i, feat in enumerate(self.flattened_features)
        ]

    def get_current_feature(self):
        return self.flattened_features[self.current_index]

    def set_current_index(self, index: int):
        if self.max_current_index == -1:
            raise Exception("Cannot call this method: flattened layer not yet created")
        if 0 <= index <= self.max_current_index:
            self.current_index = index
        else:
            raise ValueError(
                f"Incorrect index value. Must be in range: 0 - {self.max_current_index}"
            )

    def get_current_index(self):
        return self.current_index

    def count_edited_features(self):
        return len(
            list(
                filter(
                    lambda columns: len(columns) > 0,
                    [
                        feature_props.edited_fields
                        for feature_props in self.ids_and_columns
                    ],
                )
            )
        )

    def get_current_feature_edited_fields(self):
        return self.ids_and_columns[self.current_index].edited_fields

    def update_current_feature(self, key: str, value, value_changed: bool):
        """Updates current feature in flattened layer"""
        fid = self.get_current_feature().id()
        self.flattened_layer.startEditing()
        idx = self.flattened_layer.fields().indexFromName(key)
        if idx != -1:
            self.flattened_layer.changeAttributeValue(fid, idx, value)
        self.flattened_layer.commitChanges()
        self.flattened_features[self.current_index] = self.flattened_layer.getFeature(
            fid
        )
        if value_changed:
            self.ids_and_columns[self.current_index].add_column(key)
        else:
            self.ids_and_columns[self.current_index].remove_column(key)

    def get_flattened_layer(self):
        if self.flattened_layer is None:
            result = flatten_on_fly_processing(layer=self.layer.id())
            self.flattened_layer = QgsProject.instance().mapLayer(
                result["new_layer_id"]
            )
            self.flattened_features = list(self.flattened_layer.getFeatures())
            self.max_current_index = len(self.flattened_features) - 1
            # copy of original values
            for feature in self.flattened_features:
                self.original_features.append(QgsFeature(feature))
        return self.flattened_layer

    def get_current_feature_original_value(self, key: str):
        return self.original_features[self.current_index].attribute(key)

    def get_unflattened_layer(self):
        if self.unflattened_layer is None:
            self._select_edited_features()
            result = unflatten_on_fly_processing(
                layer=self.flattened_layer.id(), unflatten_selected=True
            )
            self.unflattened_layer = QgsProject.instance().mapLayer(result["layer_id"])
        return self.unflattened_layer

    def _select_edited_features(self):
        """Selects edited features from the flattened layer"""
        edited_features_ids = []
        for idx, feature_props in enumerate(self.ids_and_columns):
            if feature_props.edited_fields:
                edited_features_ids.append(self.flattened_features[idx].id())
        self.flattened_layer.selectByIds(edited_features_ids)

    def remove_unflattened_layer(self):
        self._remove_layer(self.unflattened_layer)
        self.unflattened_layer = None
        self.set_active_layer(self.flattened_layer)

    def update_layer(self):
        """Updates data back to the original layer"""
        self.layer.startEditing()
        unflattened_layer = self.get_unflattened_layer()

        for feature_props in self.ids_and_columns:
            if feature_props.edited_fields:
                here_id = feature_props.here_id
                expr = QgsExpression(f"\"id\" = '{here_id}'")
                req = QgsFeatureRequest(expr)
                f_iter = unflattened_layer.getFeatures(req)
                edited_feature = next(f_iter)
                for name in feature_props.edited_fields:
                    # name is a flattened, long key, e.g.
                    # properties.someKey.0.value
                    # I need "someKey" unflattened key
                    name = name.split(".")[1]
                    field_idx = self.layer.fields().indexOf(name)
                    self.layer.changeAttributeValue(
                        feature_props.qgis_id,
                        field_idx,
                        try_dumps_json_string(edited_feature[name]),
                    )

        self.layer.commitChanges()
