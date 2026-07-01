###############################################################################
#
# Copyright (c) 2023 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os
import sys

from qgis.core import QgsApplication

PLUGIN_NAME = "HERE QGIS Plugin"
PLUGIN_ID = "here_qgis_plugin"
PLUGIN_PACKAGE_NAME = __name__.split(".")[0]
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
SHARED_LIB_DIR = os.path.join(
    PLUGIN_DIR,
    "shared",
    "lib",
    "python{}.{}".format(sys.version_info.major, sys.version_info.minor),
)
WHEEL_DIR = os.path.join(PLUGIN_DIR, "shared")
USER_DIR = os.path.abspath(QgsApplication.qgisSettingsDirPath())
USER_PLUGIN_DIR = os.path.join(USER_DIR, PLUGIN_PACKAGE_NAME)
TMP_DIR = os.path.join(USER_PLUGIN_DIR, "tmp")
LOG_FILE_NAME = "qgis.log"
LOG_FILE = os.path.join(USER_PLUGIN_DIR, LOG_FILE_NAME)
LOCAL_REPO = os.getenv("HERE_QGIS_LOCAL_REPO", "")

os.makedirs(TMP_DIR, exist_ok=True)
