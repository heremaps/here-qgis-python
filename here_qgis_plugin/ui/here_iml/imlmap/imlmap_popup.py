###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os

from processing.tools import dataobjects
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProcessingFeedback,
    QgsProject,
)
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialog, QMessageBox
from qgis.utils import iface

from here_qgis.api.mapmaking import MapMakingAPI

from ....api_factory import create_api_for_ui
from ...here_qgis_processing.iml_layer_processing import iml_layer_processing
from ..error_msg import show_error_msg_box
from ..message_bar import show_msg_bar_error, show_msg_bar_info, show_msg_bar_warning

# default IML
DEFAULT_IML_LAYERS = [
    "address",
    "admin",
    "building",
    "carto",
    "place",
    "relation",
    "topology",
]

STYLE_MAP = [
    "No style",
    "Standard",
    "Standard Color compare (blue)",
    "Standard Color compare (red)",
    "OSM version compare color (red)",
    "OSM version compare color (blue)",
    "OSM version compare hatched (45)",
    "OSM version compare hatched (135)",
]

FILE_TYPE = [
    "GEOPACKAGE",
    "GEOJSON",
]

FEEDBACK = QgsProcessingFeedback()
CONTEXT = dataobjects.createContext(FEEDBACK)


class IMLMapPopup(QDialog):
    def __init__(self, layer_ids, catalog_hrn, name, description, parent=None):
        QDialog.__init__(self, parent)
        self.parent = parent
        self.load_ui()
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Set data
        self.hrnLabel.setText(f"HRN: {catalog_hrn}")
        self.nameLabel.setText(f"Name: {name}")
        self.descriptionText.setText(description)
        self.descriptionText.setFixedHeight(70)
        self.layer_list_widget.setFixedHeight(100)

        self.catalog_hrn = catalog_hrn  # Store HRN for catalog_hrn
        self.layer_ids = layer_ids

        # Populate layer list with checkboxes
        self.layer_list_widget.clear()

        for layer_id in layer_ids:
            self.layer_list_widget.addItem(layer_id)

        if not layer_ids:
            self.layer_list_widget.addItem("No layers available")
            self.layer_list_widget.setEnabled(False)
            self.select_all_checkbox.setEnabled(False)

        self.style_dropdown.addItems(STYLE_MAP)
        self.style_dropdown.setCurrentIndex(1)  # Set 'Standard' as the default value

        self.filetype_dropdown.addItems(FILE_TYPE)
        self.filetype_dropdown.setCurrentText(
            "GEOPACKAGE"
        )  # Set 'GEOPACKAGE' as the default value

        # Connect events
        self.extent_input.extentChanged.connect(self.move_canvas_to_extent)
        self.cancelButton.clicked.connect(self.reject)  # Close popup
        self.loadButton.clicked.connect(self.load_data)
        self.extent_button.clicked.connect(
            self.set_current_extent
        )  # Set ROI button logic
        self.select_all_checkbox.stateChanged.connect(self.toggle_select_all_layers)
        # Layer list initialization
        self.populate_layer_checkboxes()

    def load_ui(self):
        ui_path = os.path.join(os.path.dirname(__file__), "imlmap_popup.ui")
        uic.loadUi(ui_path, self)

    def populate_layer_checkboxes(self):
        """Populate the checkbox list with layers and set default states."""
        layers = set(DEFAULT_IML_LAYERS)
        for i in range(self.layer_list_widget.count()):
            item = self.layer_list_widget.item(i)
            layer_id = item.text()

            # Initial default layers to load
            if layer_id in layers:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)

        self.select_all_checkbox.setChecked(self.is_all_layers_checked())

    def is_all_layers_checked(self):
        """Check if all layers in the list are checked."""
        for i in range(self.layer_list_widget.count()):
            item = self.layer_list_widget.item(i)
            if item.checkState() != Qt.CheckState.Checked:
                return False
        return True

    def move_canvas_to_extent(self):
        """Update the extent field and pan the map when the extent changes."""

        # Get the current map's CRS
        canvas = iface.mapCanvas()

        # Get the current extent from QgsExtentWidget
        extent = self.extent_input.outputExtent()
        crs = self.extent_input.outputCrs()
        # Check if extent is valid
        if extent and not extent.isEmpty():
            # Transform input crs to current canvas crs
            crs_canvas = canvas.mapSettings().destinationCrs()
            transform = QgsCoordinateTransform(crs, crs_canvas, QgsProject.instance())
            # Pan the QGIS map to the updated extent
            iface.mapCanvas().setExtent(transform.transform(extent))
            iface.mapCanvas().refresh()

    def set_current_extent(self):
        """Set the extent field to the current map canvas bounds (EPSG:3857)."""
        canvas = iface.mapCanvas()
        extent = canvas.extent()

        # Transform current canvas map crs to default crs
        crs_default = QgsCoordinateReferenceSystem("EPSG:4326")
        crs_canvas = canvas.mapSettings().destinationCrs()
        transform = QgsCoordinateTransform(
            crs_canvas, crs_default, QgsProject.instance()
        )

        # Set extent and crs in the QgsExtentWidget
        self.extent_input.setOutputExtentFromUser(
            transform.transform(extent), crs_default
        )

    def get_linked_project_hrn(self, catalog_hrn):
        try:
            mm_api = create_api_for_ui(MapMakingAPI)
            lst_project_hrn = mm_api.get_all_linked_project_hrn(catalog_hrn)
            return lst_project_hrn[0] if lst_project_hrn else ""
        except Exception as e:
            show_error_msg_box(e, f"Failed to get project_hrn of catalog {catalog_hrn}")
        return ""

    def toggle_select_all_layers(self, state):
        """Select or unselect all layers based on the checkbox state."""
        check_state = (
            Qt.CheckState.Checked
            if state == Qt.CheckState.Checked
            else Qt.CheckState.Unchecked
        )
        for i in range(self.layer_list_widget.count()):
            item = self.layer_list_widget.item(i)
            item.setCheckState(check_state)

    def on_task_completed(self, context, params, catalog_type, successful, results):
        """
        Callback for when the processing task is successfully completed.
        Basic logic:
            - If at least one layer has success=True and
              at least one layer has success=False:
              Show "Partial Success"

            - If all layers have success=True:
              Show "Success"

            - If all layers have success=False (no data / errors):
              Show "Failure"

        Simple examples from results:
            - {'address': success=False, 'topology': success=True}
              Partial Success

            - {'address': success=True, 'topology': success=True}
              Success

            - {'address': success=False, 'topology': success=False}
              Failure
        """

        catalog_str = f'Catalog {params["catalog_hrn"]}'
        if successful and results:
            input_layers = set(params.get("iml_layers", []))
            output_layers = set(results.keys())
            missing_layers = list(input_layers - output_layers)
            failed_layers = []
            success_layers = []
            errors = {}

            for layer_id, layer_info in results.items():
                if layer_id == "success":
                    continue

                if not isinstance(layer_info, dict):
                    continue

                if layer_info.get("success"):
                    success_layers.append(layer_id)
                else:
                    failed_layers.append(layer_id)
                    error_msg = layer_info.get("error", "Unknown error")
                    errors[layer_id] = error_msg

            for missing_layer in missing_layers:
                errors[missing_layer] = "Missing layer"

            # message
            if success_layers and (failed_layers or missing_layers):
                show_msg_bar_warning(
                    msg=(
                        f"{catalog_str} - loaded partially!\n Successful layers:"
                        f" {', '.join(success_layers)}\n Failed layers:"
                        f" {', '.join(failed_layers + missing_layers)}\n Errors:"
                        f" {errors}"
                    ),
                    title="Partial Success",
                )

            elif success_layers:
                show_msg_bar_info(
                    msg=f"{catalog_str} - loaded successfully!", title="Success"
                )
            else:
                show_msg_bar_warning(
                    (
                        f"{catalog_str} - All layers fail to load. Failed layers:"
                        f" {', '.join(failed_layers + missing_layers)}\n Errors:"
                        f" {errors}"
                    ),
                    title="Failure",
                )
        else:
            show_msg_bar_error(
                (
                    f"Unexpected errors when loading catalog {catalog_str}"
                    " Please check the logs for details."
                ),
                title="Critical",
            )

    def load_data(self):
        """Load IML Layer into GeoPackage."""

        selected_layers = [
            self.layer_list_widget.item(i).text()
            for i in range(self.layer_list_widget.count())
            if self.layer_list_widget.item(i).checkState() == Qt.CheckState.Checked
        ]

        selected_style_index = self.style_dropdown.currentIndex()
        selected_filetype = self.filetype_dropdown.currentText()

        extent = self.extent_input.outputExtent()
        crs = self.extent_input.outputCrs().authid()

        extent_str = (
            f"{extent.xMinimum()},{extent.xMaximum()},"
            f"{extent.yMinimum()},{extent.yMaximum()} [{crs}]"
        )

        project_hrn = self.get_linked_project_hrn(self.catalog_hrn)

        if not crs:
            QMessageBox.warning(self, "Warning", "Please select ROI or bookmarks.")
            return
        if not selected_layers:
            QMessageBox.warning(self, "Warning", "Please select at least one layer.")
            return
        if not project_hrn:
            QMessageBox.warning(self, "Warning", "No project HRN found.")
            return

        iml_layer_processing(
            project_hrn=project_hrn,
            catalog_hrn=self.catalog_hrn,
            layer_id=selected_layers,
            extent_str=extent_str,
            style_set=selected_style_index,
            file_type=selected_filetype,
            context=CONTEXT,
            feedback=FEEDBACK,
            on_task_completed=self.on_task_completed,
        )

        self.accept()  # Close popup after execution
