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

from ....api_factory import create_api_for_ui
from ..error_msg import show_error_msg_box
from .imlmap_popup import IMLMapPopup  # Import IMLMapPopup


class IMLMaps(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Initialize UI
        self.load_imlmaps_ui()

        # Initialize variables
        self.items = []
        self.filtered_items = []
        self.current_page = 1
        self.items_per_page = 10
        # Fetch data
        self.fetch_release_maps()

    def load_imlmaps_ui(self):
        # Load the UI file
        ui_path = os.path.join(os.path.dirname(__file__), "imlmaps.ui")
        uic.loadUi(ui_path, self)

        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        # Connect UI elements
        self.searchLineEdit.textChanged.connect(self.update_search)
        self.prevButton.clicked.connect(self.go_to_previous_page)
        self.nextButton.clicked.connect(self.go_to_next_page)

    def fetch_release_maps(self):
        try:
            map_api = create_api_for_ui(IMLMapApi)
            self.items = map_api.fetch_release_maps()
            print("items", self.items)
            self.update_search()

        except requests.exceptions.RequestException as e:
            show_error_msg_box(e, "Failed to fetch data", parent=self)
            self.accept()

    def update_search(self):
        search_term = self.searchLineEdit.text().lower()
        self.filtered_items = [
            item
            for item in self.items
            if search_term in item["hrn"].lower()
            or search_term in item["name"].lower()
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
            self.dataTable.setItem(row_idx, 1, self.create_wrapped_item(item["hrn"]))
            self.dataTable.setItem(row_idx, 2, self.create_wrapped_item(item["name"]))
            self.dataTable.setItem(
                row_idx, 3, self.create_wrapped_item(item.get("summary", ""))
            )
            self.dataTable.setItem(
                row_idx,
                4,
                self.create_wrapped_item(
                    self.truncate_text(item.get("description", ""), 50)
                ),
            )
            self.dataTable.setItem(
                row_idx, 5, self.create_wrapped_item(self.format_date(item["created"]))
            )

            open_button = QPushButton("Open")
            # open_button.setFixedHeight(50)
            # open_button.setStyleSheet("margin: 5px; padding: 5px;")
            open_button.setStyleSheet(
                "margin: 5px; padding: 5px; min-height: 30px; max-height: 30px;"
            )

            open_button.clicked.connect(
                lambda _, catalog_hrn=item["hrn"], catalog_name=item[
                    "name"
                ], catalog_description=item["description"]: self.open_popup(
                    catalog_hrn, catalog_name, catalog_description
                )
            )
            self.dataTable.setCellWidget(row_idx, 6, open_button)

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

    def get_layer_ids_by_hrn(self, catalog_hrn):
        for item in self.items:
            if item.get("hrn") == catalog_hrn:
                return [
                    layer.get("id") for layer in item.get("layers", []) if "id" in layer
                ]
        return []

    def open_popup(self, catalog_hrn, name, description):
        popup = IMLMapPopup(
            self.get_layer_ids_by_hrn(catalog_hrn),
            catalog_hrn,
            name,
            description,
            self,
        )
        popup.show()
