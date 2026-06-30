###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os

import requests
from qgis.core import QgsMapLayerProxyModel, QgsVectorLayer
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import Qt

from here_qgis.api.mapmaking import MapMakingAPI

from ....api_factory import create_api_for_ui
from ....processing_toolbox.get_and_load import DEFAULT_IML_LAYERS as LAYERS
from ....processing_toolbox.layer_metadata import LayerMetadata
from ...here_qgis_processing.upload_mapmaking_processing import (
    upload_mapmaking_processing,
)
from ..error_msg import show_error_msg_box
from ..message_bar import show_msg_bar_info


class UploadMapDialog(QtWidgets.QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())

        self.iface = iface
        self.layer = self.iface.activeLayer()
        self.map_types = ["input", "livemap"]
        self.projects = []
        self.selected_feature_only = False

        self.get_project_data()  # Fetch project data from HERE Mapmaking API
        self.load_ui()

        if isinstance(self.layer, QgsVectorLayer):
            self.mapLayerComboBox.setLayer(self.layer)

    def load_ui(self):
        ui_path = os.path.join(os.path.dirname(__file__), "upload_map.ui")
        uic.loadUi(ui_path, self)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self.mapLayerComboBox.setFilters(QgsMapLayerProxyModel.Filter.VectorLayer)

        # self.horizontalLayout_5.setStretch(0, 1)
        # self.horizontalLayout_5.setStretch(1, 1)

        self.mapLayerComboBox.layerChanged.connect(self.on_layer_changed)

        self.layerTypeComboBox.addItems(["Not Selected"] + LAYERS + ["other"])
        self.layerTypeComboBox.currentTextChanged.connect(self.handle_layer_type_change)

        # projects
        self.project_id_map = {
            project["projectId"]: project for project in self.projects
        }
        self.projectComboBox.addItem("Select a project", None)
        for project in self.projects:
            project_name = project["configuration"]["name"]
            project_id = project["projectId"]
            self.projectComboBox.addItem(project_name + ": " + project_id)
        self.projectComboBox.currentTextChanged.connect(self.handle_project_change)

        self.catalogHRNText.setFixedHeight(30)

        # Selected Feature
        self.selectedFeatureCheckBox.stateChanged.connect(
            lambda state: setattr(self, "selected_feature_only", bool(state))
        )
        # Connect buttons
        self.uploadButton.clicked.connect(self.upload_map_layer)
        self.cancelButton.clicked.connect(self.reject)

    def on_layer_changed(self, layer):
        layer_id = LayerMetadata.get_layer_id(layer)
        self.layerTypeComboBox.setCurrentText(layer_id)

    def handle_layer_type_change(self, text):
        if text == "other":
            self.otherLayerTypeLineEdit.setVisible(True)
            self.otherLayerTypeLineEdit.textChanged.connect(
                self.update_selected_layer_id
            )
        else:
            self.otherLayerTypeLineEdit.setVisible(False)
            self.selectedLayerId = text

    def update_selected_layer_id(self, new_text):
        self.selectedLayerId = new_text

    def get_project_data(self):
        """Get project data from the HERE Mapmaking API."""
        try:
            map_making_api = create_api_for_ui(MapMakingAPI)
            self.projects = map_making_api.fetch_map_projects()
        except requests.exceptions.RequestException as e:
            show_error_msg_box(e, "Failed to fetch data", parent=self)

    def handle_project_change(self, index):
        # Get the data (projectId) for the selected index
        project_id = index.split(": ")[-1]

        if project_id and project_id in self.project_id_map:
            self.selectedProject = self.project_id_map[project_id]

            # Find 'input' format HRN from resources
            input_hrn = None
            for resource in self.selectedProject.get("resources", []):
                if resource.get("format") == "input":
                    input_hrn = resource.get("value", {}).get("hrn")
                    break

            if input_hrn:
                self.catalogHRNText.setText(input_hrn)
            else:
                self.layerCatalogLabel.setText("Catalog HRN:")
                print("No input HRN found in resources.")

    def upload_map_layer(self):
        try:
            selected_layer = self.mapLayerComboBox.currentLayer()
            LayerMetadata.get_project_hrn(selected_layer)
            LayerMetadata.get_layer_id(selected_layer)

            print(f"selected_layer: {selected_layer}")
            print(f"selectedLayerId: {self.selectedLayerId}")
            print(f"selectedProject: {self.selectedProject['projectHrn']}")
            print(f"selected_feature_only: {self.selected_feature_only}")
            # print(f"project_hrn: {project_hrn}")
            # print(f"layer_type: {layer_type}")

            upload_mapmaking_processing(
                project_hrn=self.selectedProject["projectHrn"],
                layer_id=self.selectedLayerId,
                map_type="input",
                upload_layer=selected_layer.id(),
                upload_selected_only=self.selected_feature_only,
            )

            show_msg_bar_info(
                title="Successful",
                msg=f"Layer '{selected_layer.name()}' uploaded successfully.",
            )

            self.accept()  # Close the dialog on success

        except Exception as e:
            show_error_msg_box(
                e,
                "An error occurred while uploading the layer",
                parent=self,
                details=dict(
                    project_hrn=self.selectedProject["projectHrn"],
                    mom_layer_id=self.selectedLayerId,
                ),
            )
