###############################################################################
#
# Copyright (c) 2023 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from typing import Optional

from qgis.core import QgsSettings
from qgis.PyQt import QtCore

SETTINGS_CRED_PATH = "here_qgis_plugin/default/credential_path"
SETTINGS_PROJECT_HRN = "here_qgis_plugin/default/project_hrn"
SETTINGS_CATALOG_HRN = "here_qgis_plugin/default/catalog_hrn"
SETTINGS_VML_CATALOG_HRN = "here_qgis_plugin/default/vml_catalog_hrn"
QT_VERSION = QtCore.qVersion().split(".")[0]


class _SettingKey:
    SETTING_KEY = "here_qgis_plugin"

    @classmethod
    def get_value(cls, default: Optional[str] = ""):
        return QgsSettings().value(cls.SETTING_KEY, default) or default

    @classmethod
    def save_value(cls, value: Optional[str]):
        if value is None:
            return False
        QgsSettings().setValue(cls.SETTING_KEY, value)
        return True

    @classmethod
    def clear_value(cls):
        QgsSettings().remove(cls.SETTING_KEY)


class UIToolbarsSetting(_SettingKey):
    SETTING_KEY = "here_qgis_plugin/ui/toolbars/default_key"
    KEY_DEV = "dev"
    KEY_MAPMAKING = "mapmaking"
    OPTIONS = [KEY_MAPMAKING, KEY_DEV]


def get_path():
    return QgsSettings().value(SETTINGS_CRED_PATH, "")


def save_path(path):
    QgsSettings().setValue(SETTINGS_CRED_PATH, path)


def clear_path():
    """Clear stored token."""
    QgsSettings().remove(SETTINGS_CRED_PATH)


def get_project_hrn():
    return QgsSettings().value(SETTINGS_PROJECT_HRN, "")


def save_project_hrn(project_hrn: str):
    QgsSettings().setValue(SETTINGS_PROJECT_HRN, project_hrn)


def clear_project_hrn():
    QgsSettings().remove(SETTINGS_PROJECT_HRN)


def get_catalog_hrn():
    return QgsSettings().value(SETTINGS_CATALOG_HRN, "")


def save_catalog_hrn(catalog_hrn: str):
    QgsSettings().setValue(SETTINGS_CATALOG_HRN, catalog_hrn)


def clear_catalog_hrn():
    QgsSettings().remove(SETTINGS_CATALOG_HRN)


def get_vml_catalog_hrn():
    return QgsSettings().value(SETTINGS_VML_CATALOG_HRN, "")


def save_vml_catalog_hrn(catalog_hrn: str):
    QgsSettings().setValue(SETTINGS_VML_CATALOG_HRN, catalog_hrn)


def clear_vml_catalog_hrn():
    QgsSettings().remove(SETTINGS_VML_CATALOG_HRN)


def isQt6():
    return QT_VERSION == "6"
