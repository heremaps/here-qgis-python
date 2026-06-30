###############################################################################
#
# Copyright (c) 2023 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import copy
import json
import logging
import os
import re
import tempfile
import time
from typing import Dict, Optional, Tuple

import geopandas as gpd
import pandas as pd
from geojson import FeatureCollection

from here_qgis.helper_functions import (
    CLICK_KEEP_UNAVAILABLE_LAYERS,
    EMPTY_FILE,
    try_dumps_json_string,
)

logger = logging.getLogger(__name__)


class LayerStorage:
    def __init__(
        self,
        layer_name: str,
        catalog_hrn: str,
        features: FeatureCollection,
        base_dir: str = "",
    ):
        self.layer_name = layer_name
        self.features = copy.deepcopy(features)
        self.filename = None
        self.timestr = time.strftime("%Y%m%d-%H%M%S")
        base_dir = base_dir or tempfile.mkdtemp(prefix="here_qgis-")
        self.folder_name = os.path.join(base_dir, catalog_hrn.replace(":", "_"))
        self.gdf = None
        self.is_geojson = False
        self.is_geopackage = False

    def create_dir(self):
        """
        Creates folder based on the catalog hrn
        """
        if not os.path.exists(self.folder_name):
            os.makedirs(self.folder_name)

    def _save_to_file(self):
        geom_types_filenames = dict()
        for geom_type in sorted(self.gdf.geom_type.unique()):
            filtered_gdf = self.gdf[self.gdf.geom_type == geom_type]
            if self.is_geopackage:
                geom_types_filenames[geom_type] = filename = self.filename
                filtered_gdf.to_file(
                    filename,
                    driver="GPKG",
                    layer=f'{self.layer_name.replace(" ", "_")}_{geom_type}',
                    mode="w",
                )
            elif self.is_geojson:
                filename = self.filename.replace(".geojson", f"_{geom_type}.geojson")
                geom_types_filenames[geom_type] = filename
                filtered_gdf.to_file(
                    filename,
                    driver="GeoJSON",
                    mode="w",
                )
        return geom_types_filenames

    def _prepare_to_save(self, ext: str):
        self.create_dir()
        # if self.filename is None or "from-platform" in self.filename:
        if self.filename is None:
            self.filename = os.path.join(
                self.folder_name, f"{self.layer_name}_{self.timestr}.{ext}"
            )

    def _from_features_to_file(self, ext: str):
        self._prepare_to_save(ext)
        geom_types_filenames = self._save_to_file()

        # after save need to set back to false,
        # so the user can use the same LayerStorage object
        self.is_geojson = self.is_geopackage = False
        return geom_types_filenames

    def from_features_to_geojson(self):
        """Dumps Feature Collection into .geojson file"""
        self.is_geojson = True
        return self._from_features_to_file("geojson")

    def from_features_to_geopackage(self):
        """Dumps Feature Collection into .gpkg file"""
        self.is_geopackage = True
        return self._from_features_to_file("gpkg")

    def add_features_to_file(
        self, old_filename, layername, is_v1_layer=False, is_reloaded=False
    ) -> Tuple[Optional[str], Optional[bool], Optional[Dict[str, str]]]:
        """Function adds features to the existing file
        (or creates new if old_filename == EMPTY_FILE)

        :param str old_filename: Old filename

        :param str layername: Layer name

        :param bool is_v1_layer: If layer was created by HERE PluginV1

        :param is_reloaded: If layer was already reloaded

        :return Tuple[Optional[str], Optional[bool], Optional[dict[str, str]]]:
            new filename, if layer is carto layer, dict with (geom_type, filename)
        """
        is_carto = "carto" in old_filename.lower() or "carto" in layername.lower()
        gpkg_match = re.search(".gpkg", old_filename)
        gdf_old = None

        if not (
            old_filename == EMPTY_FILE or old_filename == CLICK_KEEP_UNAVAILABLE_LAYERS
        ):
            if is_carto:
                layer_match = re.search("layername=", old_filename)
                layer = old_filename[layer_match.end() :]
                old_filename = old_filename[: gpkg_match.end()]
                gdf_old = gpd.read_file(old_filename, layer=layer, encoding="utf-8")
            else:
                old_filename = old_filename[: gpkg_match.end()]
                gdf_old = gpd.read_file(old_filename, encoding="utf-8")

            if is_v1_layer and not is_reloaded:
                old_timestamp_index = old_filename.find("__")
                self.filename = (
                    old_filename[: old_timestamp_index + 2] + self.timestr + ".gpkg"
                )
            else:
                timestamp_pattern = r"(\d{8}-\d{6})"
                match = re.search(timestamp_pattern, old_filename)

                if match is not None:
                    start_index, end_index = match.span()
                    self.filename = (
                        old_filename[:start_index]
                        + self.timestr
                        + old_filename[end_index:]
                    )
                else:
                    raise ValueError("Incorrect filename.")

        self.process_features()
        if not (
            old_filename == EMPTY_FILE or old_filename == CLICK_KEEP_UNAVAILABLE_LAYERS
        ):
            gdf_combined = pd.concat([self.gdf, gdf_old], ignore_index=True)
            self.gdf = gpd.GeoDataFrame(gdf_combined)
        if self.gdf.empty:
            return None, None, None

        geom_filenames = self.from_features_to_geopackage()
        return self.filename, is_carto, geom_filenames

    def features_to_geojson(self):
        self.create_dir()
        filename = os.path.join(
            self.folder_name, f"{self.layer_name}-{self.timestr}-from-platform.geojson"
        )

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.features, f, ensure_ascii=False)

        return filename

    def process_features(self):
        # TODO: better handling feature error
        excluded_columns = ["geometry"]

        for feature in self.features["features"]:
            try:
                feature["properties"]["momType"] = feature["momType"]
                feature["properties"]["id"] = feature["id"]
            except KeyError as e:
                logger.error("Error parsing momtype and id. %s", e)
            for key, value in feature["properties"].items():
                if key in excluded_columns:
                    continue
                feature["properties"][key] = try_dumps_json_string(value)
        gdf = gpd.GeoDataFrame.from_features(self.features)

        # return gdf
        self.gdf = gdf
