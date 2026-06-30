###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os

from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialog

from ....processing_toolbox.basemap_processing_toolbox import LoadBasemap
from ...here_qgis_processing.basemap_processing import basemap_tile_processing
from ..error_msg import show_error_msg_box


class Basemap(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), "basemap.ui")
        uic.loadUi(ui_path, self)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Populate dropdowns
        self.imageFormatDropdown.addItems(LoadBasemap.IMAGE_FORMATS)
        self.imageFormatDropdown.setCurrentText("png")  # Default

        self.imageSizeDropdown.addItems(LoadBasemap.IMAGE_SIZES)
        self.imageSizeDropdown.setCurrentText("256")  # Default

        self.mapStyleDropdown.addItems(LoadBasemap.MAP_TILE_STYLES)
        self.mapStyleDropdown.setCurrentText("explore.day")  # Default

        self.languageDropdown.addItems(
            ["--Not Selected--"] + LoadBasemap.LANGUAGES
        )  # Optional
        self.languageSecDropdown.addItems(
            ["--Not Selected--"] + LoadBasemap.LANGUAGES
        )  # Optional
        self.pviewDropdown.addItems(
            ["--Not Selected--"] + LoadBasemap.GEOPOLITICAL_VIEWS
        )  # Optional

        # Style
        self.languageDropdown.setStyleSheet("QComboBox { combobox-popup: 0; }")
        self.languageSecDropdown.setStyleSheet("QComboBox { combobox-popup: 0; }")
        self.pviewDropdown.setStyleSheet("QComboBox { combobox-popup: 0; }")

        # Connect Buttons
        self.loadButton.clicked.connect(self.apply_settings)
        self.cancelButton.clicked.connect(self.reject)  # Close window on Cancel

    def safe_index(self, lst, value, default=None):
        try:
            return lst.index(value)
        except ValueError:
            return default

    def safe_value(self, lst, value, default=None):
        return value if value in lst else default

    def apply_settings(self):
        """Load HERE basemap with selected settings and apply the bookmark extent."""
        selected_style = self.mapStyleDropdown.currentText()
        selected_format = self.imageFormatDropdown.currentText()
        selected_size = self.imageSizeDropdown.currentText()
        selected_lang = self.languageDropdown.currentText()
        selected_lang_sec = self.languageDropdown.currentText()
        selected_pview = self.pviewDropdown.currentText()

        styles = self.safe_value(LoadBasemap.MAP_TILE_STYLES, selected_style, None)
        image_formats = self.safe_value(
            LoadBasemap.IMAGE_FORMATS, selected_format, None
        )
        image_sizes = self.safe_value(LoadBasemap.IMAGE_SIZES, selected_size, None)
        langs = self.safe_value(LoadBasemap.LANGUAGES, selected_lang, None)
        langs_sec = self.safe_value(LoadBasemap.LANGUAGES, selected_lang_sec, None)
        pview = self.safe_value(LoadBasemap.GEOPOLITICAL_VIEWS, selected_pview, None)
        try:
            basemap_tile_processing(
                styles=styles,
                imageFormats=image_formats,
                imageSizes=image_sizes,
                feature="",
                langs=langs,
                langs_sec=langs_sec,
                pview=pview,
            )

            self.accept()  # Close the window after applying settings
        except Exception as e:
            show_error_msg_box(
                error=e,
                message="An error occured during loading base map",
                parent=self,
                details=dict(
                    styles=styles,
                    image_formats=image_formats,
                    image_sizes=image_sizes,
                    langs=langs,
                    langs_sec=langs_sec,
                    pview=pview,
                ),
            )
