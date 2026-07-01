###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os
from datetime import datetime

import requests
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QHeaderView, QPushButton, QTableWidgetItem

from here_qgis.api.map import IMLMapApi
from here_qgis.api.mapmaking import MapMakingAPI

from ....api_factory import create_api_for_ui
from ...utils.settings_manager import set_auth_status
from ..error_msg import show_error_msg_box
from ..imlmap.imlmap_popup import DEFAULT_IML_LAYERS
from .mapmaking_popup import MapmakingPopup  # Import IMLMapPopup


class MapmakingProjectLoad(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Initialize UI
        self.load_imlmaps_ui()

        # Initialize variables
        self.items = []
        self.filtered_items = []
        self.current_page = 1
        self.items_per_page = 10
        self.auth_status = False
        self._layer_cache = {}
        # Project data
        self.get_project_data()

    def load_imlmaps_ui(self):
        # Load the UI file
        ui_path = os.path.join(os.path.dirname(__file__), "mapmaking.ui")
        uic.loadUi(ui_path, self)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Connect UI elements
        self.searchLineEdit.textChanged.connect(self.update_search)
        self.prevButton.clicked.connect(self.go_to_previous_page)
        self.nextButton.clicked.connect(self.go_to_next_page)

    def get_layer_ids(self, catalog_hrn, project_hrn):
        """
        Get layer IDs for the livemap catalog.
        Uses cached layer IDs when available.
        Returns API-fetched layer IDs, or default layers if the request fails.

        Returns:
            List of layer IDs.
        """
        if catalog_hrn in self._layer_cache:
            return self._layer_cache[catalog_hrn]

        map_api = create_api_for_ui(IMLMapApi, project_hrn)
        try:
            layer_ids = map_api.get_layer_ids(catalog_hrn)
            # Store cache
            self._layer_cache[catalog_hrn] = layer_ids
            return layer_ids
        except Exception:
            return DEFAULT_IML_LAYERS

    def get_project_data(self):
        """Get project data from the HERE Mapmaking API."""
        try:
            map_making_api = create_api_for_ui(MapMakingAPI)
            self.items = map_making_api.fetch_map_projects()
            self.update_search()
            self.auth_status = True
        except requests.exceptions.RequestException as e:
            if e.response.status_code == 401:
                self.auth_status = False
                set_auth_status(False)
                show_error_msg_box(
                    None,
                    "Your token probably expired. Try to login again.",
                    parent=self,
                )
            else:
                show_error_msg_box(e, "Failed to fetch data", parent=self)
            self.accept()

    def check_auth_status(self):
        return self.auth_status

    def update_search(self):
        search_term = self.searchLineEdit.text().lower()
        self.filtered_items = [
            item
            for item in self.items
            if search_term in item["projectHrn"].lower()
            or search_term in item["configuration"]["name"].lower()
            or search_term in item["created"].lower()
        ]
        self.current_page = 1
        self.display_data()

    def create_wrapped_item(self, text):
        table_item = QTableWidgetItem(text)
        table_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        table_item.setFlags(table_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        return table_item

    def format_date(self, date_str):
        # Convert the string to a datetime object
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        # Format the datetime object into a desired string format
        formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")

        return formatted_date

    def truncate_text(self, text, length=30):
        """Truncate text to a specified length with '...' if it's too long."""
        return text if len(text) <= length else text[:length] + "..."

    def display_data(self):
        self.dataTable.setRowCount(0)
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page
        current_items = self.filtered_items[start_idx:end_idx]

        for row_idx, item in enumerate(current_items):
            self.dataTable.insertRow(row_idx)
            self.dataTable.setItem(
                row_idx, 0, self.create_wrapped_item(str(start_idx + row_idx + 1))
            )
            self.dataTable.setItem(
                row_idx, 1, self.create_wrapped_item(item["configuration"]["name"])
            )
            self.dataTable.setItem(
                row_idx, 2, self.create_wrapped_item(item["projectId"])
            )
            self.dataTable.setItem(
                row_idx, 3, self.create_wrapped_item(item["projectHrn"])
            )
            self.dataTable.setItem(
                row_idx, 4, self.create_wrapped_item(self.format_date(item["created"]))
            )

            open_button = QPushButton("Open")
            # open_button.setFixedHeight(50)
            # open_button.setStyleSheet("margin: 5px; padding: 5px;")
            open_button.setStyleSheet(
                "margin: 5px; padding: 5px; min-height: 30px; max-height: 30px;"
            )

            name = item["configuration"]["name"]
            description = item["configuration"]["description"]
            project_hrn = item["projectHrn"]
            input_catalog_hrn = next(
                r["value"]["hrn"] for r in item["resources"] if r["format"] == "input"
            )
            livemap_catalog_hrn = next(
                r["value"]["hrn"] for r in item["resources"] if r["format"] == "livemap"
            )

            open_button.clicked.connect(
                lambda _, name=name, description=description, project_hrn=project_hrn, input_catalog_hrn=input_catalog_hrn, livemap_catalog_hrn=livemap_catalog_hrn: self.open_popup(  # noqa
                    name,
                    description,
                    project_hrn,
                    input_catalog_hrn,
                    livemap_catalog_hrn,
                )
            )
            self.dataTable.setCellWidget(row_idx, 5, open_button)

        # Adjust column widths
        column_count = self.dataTable.columnCount()

        # Set column 0 to fit content
        self.dataTable.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )

        # Last column (button) fit content
        self.dataTable.horizontalHeader().setSectionResizeMode(
            column_count - 1, QHeaderView.ResizeMode.ResizeToContents
        )

        # Set other columns to stretch
        for col in range(1, column_count - 1):
            self.dataTable.horizontalHeader().setSectionResizeMode(
                col, QHeaderView.ResizeMode.Stretch
            )

        # Enable text wrapping
        self.dataTable.setWordWrap(True)

        # Auto-adjust row height for wrapped text
        self.dataTable.resizeRowsToContents()

        total_pages = max(1, -(-len(self.filtered_items) // self.items_per_page))
        # self.pageLabel.setText(f"Page {self.current_page} of {total_pages}")
        self.prevButton.setEnabled(self.current_page > 1)
        self.nextButton.setEnabled(self.current_page < total_pages)
        self.pageLabel.setText(
            f"Items ({start_idx + 1}-{min(end_idx, len(self.filtered_items))}) of"
            f" {len(self.filtered_items)}"
        )

    def go_to_previous_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.display_data()

    def go_to_next_page(self):
        total_pages = max(1, -(-len(self.filtered_items) // self.items_per_page))
        if self.current_page < total_pages:
            self.current_page += 1
            self.display_data()

    def open_popup(
        self, name, description, project_hrn, input_catalog_hrn, livemap_catalog_hrn
    ):
        popup = MapmakingPopup(
            self.get_layer_ids(livemap_catalog_hrn, project_hrn),
            project_hrn,
            livemap_catalog_hrn,
            input_catalog_hrn,
            name,
            description,
            self,
        )
        popup.show()
