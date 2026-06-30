# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os
import sys
import sysconfig

from qgis.core import QgsApplication, QgsSettings

from ....utils.dependencies import is_module_missing

QML_DIR = os.path.dirname(os.path.abspath(__file__))


def get_qml_full_path(qml_file):
    return os.path.join(QML_DIR, qml_file)


def check_webengine_qml(isolated: bool):
    """Check for QtWebEngine bundled qml files, installed qml files and python module.
    If both not exist, then qml dependencies should be installed
    """
    return (
        (
            check_qgis_qml_path()
            or check_qml_import_paths()
            or not is_module_missing("PyQt5.QtWebEngine")
        )
        if isolated
        else check_qgis_qml_path()
    )


def check_qgis_qml_path():
    """Check WebEngine qml bundled in QGIS"""
    qgis_qml_paths = {
        qml_path: os.listdir(qml_path)
        for qml_base_path in [
            os.path.join(os.environ.get("OSGEO4W_ROOT", ""), "apps", "Qt5"),
            os.path.join(os.environ.get("OSGEO4W_ROOT", ""), "apps", "qt5"),
            os.environ.get("O4W_QT_PREFIX", ""),
            # apps/qgis : libexecPath, pkgDataPath, prefixPath
            # apps/qgis/lib : libraryPath , apps/qgis/plugins : pluginPath
            os.path.join(QgsApplication.libexecPath(), "..", "Qt5"),
            os.path.join(QgsApplication.libexecPath(), "..", "qt5"),
        ]
        for qml_path in [
            os.path.join(qml_base_path, "qml"),
            os.path.join(qml_base_path, "bin"),
        ]
        if os.path.exists(qml_path)
    }

    return any(
        "WebEngine".lower() in file.lower()
        for files in qgis_qml_paths.values()
        for file in files
    )


def get_dist_packages_qml_base_paths():
    """Get qml import base path from python dist-packages (debian)"""
    paths = [p for p in sys.path if "dist-packages" in p]
    pyqt5_paths = [
        entry.path
        for p in paths
        for entry in os.scandir(p)
        if entry.is_dir() and entry.name == "PyQt5"
    ]
    base_paths = [
        entry.path
        for p in pyqt5_paths
        for entry in os.scandir(p)
        if entry.is_dir() and entry.name.lower() in ["qt5", "qt"]
    ]
    return base_paths


def get_qml_import_base_path(qt_folder="Qt5"):
    """Get qml import base path from python module"""
    prefix = sysconfig.get_path("purelib")
    lib_path = f"{prefix}/PyQt5/{qt_folder}"
    try:
        import importlib.metadata

        lib_path = os.path.join(
            importlib.metadata.distribution("PyQtWebEngine").locate_file("PyQt5"),
            qt_folder,
        )
    except Exception as e:
        print(repr(e))
        # lib_path = config.get_external_os_lib()

    return lib_path


def get_conda_qml_import_base_paths():
    """
    On conda/pixi system, qml data is stored at .pixi/envs/default/qml
    So base path would be .pixi/envs/default
    On Windows, base path is .pixi/envs/default/Library
    """
    return [
        sys.prefix,
        # .pixi/envs/default/Library : libexecPath on pixi Windows
        os.path.join(QgsApplication.libexecPath()),
    ]


def check_qml_import_paths():
    """Check qml import paths from python module"""
    return len(get_qml_import_paths()) > 0


# TODO: refactor into QmlWebEngineSetup, align with os detection
def get_qml_import_paths(qml_query: str = "WebEngine"):
    """
    Get all qml import paths from python module.

    The files inside import path shall contain `qml_query` string.
    qml import paths are searched in the following order:
    + for conda/pixi system (qt-webengine, qml dir in conda base path)
    + for linux system (dist-packages)
    + for bundled QGIS: windows, macos (isolated site-packages)

    For conda/pixi system, WebEngine should be made available
    per conda/pixi package `qt-webengine`
    """
    qml_paths = {
        qml_path: os.listdir(qml_path)
        for qml_base_path in get_conda_qml_import_base_paths()
        + get_dist_packages_qml_base_paths()
        + [
            get_qml_import_base_path("Qt5"),
            get_qml_import_base_path("Qt"),
        ]
        for qml_path in [
            os.path.join(qml_base_path, "qml"),
            os.path.join(qml_base_path, "bin"),
        ]
        if os.path.exists(qml_path)
    }

    return [
        base_path
        for base_path, files in qml_paths.items()
        if any(qml_query.lower() in file.lower() for file in files)
    ]


def get_plugin_setting(key, default=""):
    key_prefix = "here_qgis_plugin/ui"
    key_ = f"{key_prefix}/{key}"
    return QgsSettings().value(key_, default)
