# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os
import platform
from collections import OrderedDict

from qgis.core import QgsSettings
from qgis.PyQt.QtGui import QSurfaceFormat

from ....settings import isQt6
from ....utils.dependencies import (
    confirm_with_dialog,
    install_packages,
    install_packages_conda,
    install_packages_pixi,
    is_conda_system,
    is_pixi_system,
)
from .qml_dependencies import (
    check_webengine_qml,
    get_plugin_setting,
    get_qml_import_paths,
)


class QmlWebEngineSetup:
    def __init__(
        self,
        try_qml_dependencies=True,
        isolated=True,
        disable_sandbox=False,
        remote_debug=False,
        fix_surface_format=False,
        qt_debug=False,
        qt6=False,
    ):
        self.try_qml_dependencies = try_qml_dependencies
        self.isolated = isolated

        self.env_vars = OrderedDict()

        self.set_env("QML_USE_GLYPHCACHE_WORKAROUND", "1")
        if remote_debug:
            self.set_env("QTWEBENGINE_REMOTE_DEBUGGING", "5000")
        if disable_sandbox:
            # works on mac
            # works on windows, qt6
            self.set_env("QTWEBENGINE_DISABLE_SANDBOX", "1")
        if qt_debug:
            self.set_env(
                "QTWEBENGINE_CHROMIUM_FLAGS",
                "--disable-gpu --enable-logging --log-level=0 --v=1 --single-process",
            )
            # self.set_env(
            #     "QTWEBENGINE_CHROMIUM_FLAGS", "--disable-software-rasterizer")

        if qt6:
            # works on windows, qt6
            self.set_env("QTWEBENGINE_CHROMIUM_FLAGS", "--single-process")
        else:
            if fix_surface_format:
                QSurfaceFormat.setDefaultFormat(
                    QSurfaceFormat()
                )  # fix for windows rdp, break mac

        self.apply_env_vars()

    @classmethod
    def from_os(cls, debug_mode=False, qt_debug=False):
        """Return proper setup based on OS"""
        isolated = True
        if is_pixi_system():
            return cls(
                try_qml_dependencies=True,
                remote_debug=debug_mode,
                qt_debug=qt_debug,
            )
        elif is_conda_system():
            return cls(
                try_qml_dependencies=True,
                remote_debug=debug_mode,
                qt_debug=qt_debug,
            )
        elif platform.system() == "Darwin" or os.name == "mac":
            # mac: isolated works since QGIS 3.36
            # mac: non-isolated to avoid errors in older QGIS: icu data, sip, qml
            # isolated = False
            return cls(
                try_qml_dependencies=True,
                isolated=isolated,
                disable_sandbox=isolated,
                remote_debug=debug_mode,
                qt_debug=qt_debug,
            )
        elif platform.system() == "Linux" or os.name == "posix":
            return cls(
                try_qml_dependencies=True,
                isolated=isolated,
                disable_sandbox=isolated,
                remote_debug=debug_mode,
                qt_debug=qt_debug,
            )
        elif platform.system() == "Windows" or os.name == "nt":
            # windows: qml_dependencies import only for outdated QGIS
            # windows: fix_surface_format for windows rdp
            return cls(
                try_qml_dependencies=False,
                fix_surface_format=True,
                qt6=isQt6(),
                remote_debug=debug_mode,
                qt_debug=qt_debug,
            )

    def install_qml_dependencies(self):
        isolated = self.isolated
        if check_webengine_qml(isolated):
            return

        package_version = self.get_version_from_settings()  # "5.15.2"
        if is_pixi_system():
            package_str = "qt-webengine"
            if package_version:
                package_str = f"{package_str}={package_version}"
            packages = [package_str]
            if confirm_with_dialog(packages, "Pixi"):
                return install_packages_pixi(packages)
        elif is_conda_system():
            package_str = "qt-webengine"
            if package_version:
                package_str = f"{package_str}={package_version}"
            packages = [package_str]
            if confirm_with_dialog(packages, "Pixi"):
                return install_packages_conda(packages)
        else:
            package_str = "PyQtWebEngine"
            if package_version:
                package_str = f"{package_str}=={package_version}"
            packages = [package_str, "PyQt5-Qt5"]
            if confirm_with_dialog(packages):
                return install_packages(packages, isolated=isolated)

    @staticmethod
    def get_version_from_settings():
        return get_plugin_setting("QtWebEngine/version")

    def add_qml_import_path(self, qml_engine):
        """Add import path to qml engine, depending on OS platform"""
        isolated = self.isolated
        if self.try_qml_dependencies:
            current_import_paths = qml_engine.importPathList()
            self.install_qml_dependencies()
            if isolated:
                for p in get_qml_import_paths():
                    if p in current_import_paths:
                        continue
                    qml_engine.addImportPath(p)
        print(qml_engine.importPathList())
        print(qml_engine.pluginPathList())

    def init_view(self):
        try:
            from PyQt5.QtQuick import QQuickView
        except ImportError:
            from PyQt6.QtQuick import QQuickView

        view = QQuickView()
        engine = view.engine()
        self.add_qml_import_path(engine)
        return view

    def set_env(self, key, value):
        os.environ[key] = value
        self.env_vars[key.strip()] = value.strip()

    def apply_env_vars(self):
        env_args = QgsSettings().value("qgis/customEnvVars", [])
        envs = OrderedDict()
        for arg in env_args:
            mode, kv = arg.split("|", 1)
            key, value = kv.split("=", 1)
            envs[f"{mode}|{key.strip()}"] = value.strip()
        for key, value in self.env_vars.items():
            envs[f"overwrite|{key}"] = value

        new_env_args = [f"{key}={value}" for key, value in envs.items()]
        QgsSettings().setValue("qgis/customEnvVars", new_env_args)
        QgsSettings().setValue("qgis/customEnvVarsUse", "true")
