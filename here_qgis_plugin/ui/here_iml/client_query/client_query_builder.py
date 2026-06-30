###############################################################################
#
# Copyright (c) 2026 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.core import QgsProject

from ...here_qgis_processing.flatten_on_fly_processing import flatten_on_fly_processing
from ..mapmaking.query_builder import NON_ARRAY_FILTER_OPTIONS, QueryBuilder


class ClientQueryBuilder(QueryBuilder):
    def __init__(self):
        super().__init__()

    def _build_query_from_key(self, key: str, value) -> str:
        updated_key = "properties." + key[2:] if key.startswith("p.") else key
        operator, only_value = value
        val_str = str(only_value)
        # Remove any spaces
        val_str = val_str.strip()
        updated_key = updated_key.strip()

        return f'"{updated_key}"{operator}{val_str}'

    def build_query(self):
        query_parts = []

        for key, value in self.filters.items():
            query_parts.append(self._build_query_from_key(key, value))

        return " AND ".join(query_parts)

    def get_matching_feature_ids(
        self,
        source_layer,
        query: str,
        id_field_flat: str = "properties.id",
    ) -> list[str]:
        """
        Applies query on a flattened layer and returns matching feature IDs.

        - source_layer: original QgsVectorLayer
        - query: QGIS expression string
        - id_field_flat: ID field name in flattened layer

        Returns: list of feature IDs
        """

        result = flatten_on_fly_processing(layer=source_layer.id())
        flat_layer = QgsProject.instance().mapLayer(result["new_layer_id"])

        if not flat_layer:
            QgsProject.instance().removeMapLayer(result["new_layer_id"])
            return []

        flat_layer.selectByExpression(query)

        ids = [
            feature[id_field_flat]
            for feature in flat_layer.selectedFeatures()
            if feature[id_field_flat] is not None
        ]

        QgsProject.instance().removeMapLayer(result["new_layer_id"])
        return ids

    def get_all_operators(self, long_key):
        return NON_ARRAY_FILTER_OPTIONS
