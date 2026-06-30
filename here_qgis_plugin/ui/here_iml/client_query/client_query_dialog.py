###############################################################################
#
# Copyright (c) 2026 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os

from qgis.core import QgsVectorLayer
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialog, QMessageBox

from ....processing_toolbox.layer_metadata import LayerMetadata
from ..mapmaking.query_build import QueryBuild
from .client_query_builder import ClientQueryBuilder


class ClientIMLQuery(QDialog):
    @classmethod
    def try_create_dialog(cls, layer: QgsVectorLayer, parent):
        if not layer:
            QMessageBox.warning(
                parent, "Warning", "No active layer found. Please select a layer."
            )
            return

        if not isinstance(layer, QgsVectorLayer):
            QMessageBox.warning(
                parent, "Warning", "Selected layer is not a vector layer."
            )
            return
        return cls(layer, parent)

    def __init__(self, layer: QgsVectorLayer, parent=None):
        super().__init__(parent)

        self.layer = layer
        self.layer_name = self.layer.id()
        self.layer_id = LayerMetadata.get_layer_id(self.layer)
        self.query_builder = ClientQueryBuilder()

        # Load UI
        self.load_ui()

        # Connect UI buttons
        self.filter_button.clicked.connect(self.show_query_builder)
        self.loadButton.clicked.connect(self.on_load_clicked)
        self.cancelButton.clicked.connect(self.close)

    def load_ui(self):
        ui_path = os.path.join(os.path.dirname(__file__), "client_query_dialog.ui")
        uic.loadUi(ui_path, self)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

    def show_query_builder(self):
        query_build = QueryBuild(self.layer_id, self.query_builder, self)
        query_build.query_to_send.connect(self.set_query)
        query_build.show()

    def set_query(self, query: str):
        self.text_query.setPlainText(query)

    def on_load_clicked(self):
        query_text = self.text_query.toPlainText().strip()
        if not query_text:
            QMessageBox.warning(self, "Warning", "No query defined")
            return

        self.apply_iml_query(self.layer, query_text)

    def apply_iml_query(self, layer, query: str):
        layer.removeSelection()
        self.text_query.setPlainText(query)

        selected_ids = self.query_builder.get_matching_feature_ids(
            source_layer=layer,
            query=query,
        )
        if not selected_ids:
            QMessageBox.information(self, "No Match", "No features matched")
            return

        quoted_ids = ",".join(f"'{fid}'" for fid in selected_ids)
        expression = f'"id" IN ({quoted_ids})'

        layer.selectByExpression(expression)

        QMessageBox.information(
            self,
            "Query Applied",
            f"Selected {len(selected_ids)} features in layer '{layer.name()}'",
        )

        self.accept()
