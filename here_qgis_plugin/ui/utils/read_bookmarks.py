###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os
import re
import xml.etree.ElementTree as ET

from qgis.core import QgsApplication, QgsRectangle


def parse_extent(extent_wkt):
    """Extracts xmin, ymin, xmax, ymax from a WKT POLYGON string."""
    match = re.search(r"POLYGON\(\(([^)]+)\)\)", extent_wkt)
    if not match:
        return None

    coords = match.group(1).split(", ")
    coords = [tuple(map(float, coord.split())) for coord in coords]

    xmin = min(x for x, y in coords)
    xmax = max(x for x, y in coords)
    ymin = min(y for x, y in coords)
    ymax = max(y for x, y in coords)

    return QgsRectangle(xmin, ymin, xmax, ymax)


def read_bookmarks():
    """Reads global bookmarks from QGIS bookmarks.xml file."""
    profile_path = QgsApplication.qgisSettingsDirPath()
    bookmarks_file = os.path.join(profile_path, "bookmarks.xml")

    bookmarks = []
    if os.path.exists(bookmarks_file):
        tree = ET.parse(bookmarks_file)
        root = tree.getroot()

        for bookmark in root.findall("Bookmark"):
            name = bookmark.get("name")
            extent_wkt = bookmark.get("extent")
            authid = bookmark.find("./spatialrefsys/authid").text

            extent = parse_extent(extent_wkt)
            if extent:
                crs = authid
                bookmarks.append((name, extent, crs))
    # print(bookmarks)
    return bookmarks
