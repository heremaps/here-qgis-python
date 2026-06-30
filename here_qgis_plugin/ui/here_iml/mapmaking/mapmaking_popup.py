###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os

from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QMessageBox

from ...here_qgis_processing.iml_layer_processing import iml_layer_processing
from ..imlmap.imlmap_popup import CONTEXT, DEFAULT_IML_LAYERS, FEEDBACK, IMLMapPopup
from .query_build import QueryBuild
from .query_builder import QueryBuilder


class MapmakingPopup(IMLMapPopup):
    def __init__(self, item, parent=None):
        IMLMapPopup.__init__(
            self,
            DEFAULT_IML_LAYERS,
            item["projectHrn"],
            item["configuration"]["name"],
            item["configuration"]["description"],
            parent=parent,
        )

        self.current_checked = ""
        self.query_builder = QueryBuilder()
        # Set data
        self.project_hrn = item["projectHrn"]
        self.catalog_hrn = None
        self.input_catalog_hrn = next(
            r["value"]["hrn"] for r in item["resources"] if r["format"] == "input"
        )
        self.livemap_catalog_hrn = next(
            r["value"]["hrn"] for r in item["resources"] if r["format"] == "livemap"
        )
        self.text_query.selectionChanged.connect(self.check_if_is_editable)
        self.filter_button.clicked.connect(self.show_query_builder)

    def check_if_is_editable(self):
        checked = 0
        self.last_checked = self.current_checked
        for i in range(self.layer_list_widget.count()):
            if self.layer_list_widget.item(i).checkState() == Qt.CheckState.Checked:
                checked += 1
                self.current_checked = self.layer_list_widget.item(i).text()
        one_checked = checked == 1
        self.text_query.setReadOnly(not one_checked)
        return one_checked

    def show_query_builder(self):
        selected_layers = self.get_selected_layers()
        if not self.check_if_is_editable():
            QMessageBox.warning(
                self, "Warning", "Please select one layer to build query."
            )
            return
        if self.last_checked != self.current_checked and self.current_checked != "":
            self.query_builder = QueryBuilder()
            self.set_query("")
        else:
            self.query_builder.add_query(self.text_query.toPlainText())
        query_build = QueryBuild(selected_layers[0], self.query_builder, self)
        query_build.query_to_send.connect(self.set_query)
        query_build.show()

    def set_query(self, query: str):
        self.text_query.setPlainText(query)

    def load_ui(self):
        ui_path = os.path.join(os.path.dirname(__file__), "mapmaking_popup.ui")
        uic.loadUi(ui_path, self)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

    def get_selected_layers(self):
        return [
            self.layer_list_widget.item(i).text()
            for i in range(self.layer_list_widget.count())
            if self.layer_list_widget.item(i).checkState() == Qt.CheckState.Checked
        ]

    def load_data(self):
        """Load IML Layer into GeoPackage."""

        selected_layers = self.get_selected_layers()

        selected_style_index = self.style_dropdown.currentIndex()
        selected_filetype = self.filetype_dropdown.currentText()

        extent = self.extent_input.outputExtent()
        crs = self.extent_input.outputCrs().authid()

        extent_str = (
            f"{extent.xMinimum()},{extent.xMaximum()},"
            f"{extent.yMinimum()},{extent.yMaximum()} [{crs}]"
        )

        if not crs:
            QMessageBox.warning(self, "Warning", "Please select ROI or bookmarks.")
            return
        if not selected_layers:
            QMessageBox.warning(self, "Warning", "Please select at least one layer.")
            return
        if not self.project_hrn:
            QMessageBox.warning(self, "Warning", "No project HRN found.")
            return

        # for live map catalog
        iml_layer_processing(
            project_hrn=self.project_hrn,
            catalog_hrn=self.livemap_catalog_hrn,
            layer_id=selected_layers,
            extent_str=extent_str,
            style_set=selected_style_index,
            file_type=selected_filetype,
            context=CONTEXT,
            query=self.text_query.toPlainText() if self.check_if_is_editable() else "",
            feedback=FEEDBACK,
            on_task_completed=self.on_task_completed,
            catalog_type="Livemap",
        )

        # for input catalog
        iml_layer_processing(
            project_hrn=self.project_hrn,
            catalog_hrn=self.input_catalog_hrn,
            layer_id=selected_layers,
            extent_str=extent_str,
            style_set=0,
            file_type=selected_filetype,
            context=CONTEXT,
            query=self.text_query.toPlainText() if self.check_if_is_editable() else "",
            feedback=FEEDBACK,
            on_task_completed=self.on_task_completed,
            catalog_type="Input",
        )

        self.accept()  # Close popup after execution
