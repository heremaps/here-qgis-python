# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2023 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os
import shutil

from qgis.PyQt.QtCore import QObject, Qt, QUrl, pyqtSignal

from ....settings import isQt6
from ...utils.settings_manager import (
    clear_sso_token,
    parse_sso_token_json,
    set_sso_token_json,
    token_expired,
)
from ..message_bar import show_msg_bar_info
from .qml_dependencies import get_qml_full_path
from .qml_web_engine import QmlWebEngineSetup


class QmlError(Exception):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)


class LoginDialog(QObject):
    LOGIN_URL = "https://platform.here.com"
    TITLE = "HERE Platform Login"

    login_finished = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.view = None
        self.token = None
        self.profilePath = None

    def create_qml_view(
        self, logout_and_close=False, logout_and_reload=False, debug_mode=False
    ):
        """Create and show the login window to HERE Platform.

        :param logout_and_close: set to True to logout and close login window
        :param logout_and_reload: set to True to logout and open login window
        :param debug_mode: load debug qml
        :return: QQuickView
        """

        debug_mode = debug_mode or os.getenv("HERE_QML_DEBUG", "") == "true"
        debug_log_html = os.getenv("HERE_QML_DEBUG_LOG", "")

        setup = QmlWebEngineSetup.from_os(debug_mode=debug_mode)
        self.view = setup.init_view()

        view_props = {"loginUrl": self.LOGIN_URL}

        if logout_and_close:
            view_props.update({"flagLogoutAndClose": "true"})
        elif logout_and_reload:
            view_props.update({"flagLogoutAndReload": "true"})

        if debug_mode:
            title = self.TITLE + " debug"
            self.view.setInitialProperties(dict(view_props, debugMode="true"))
            if isQt6():
                self.view.setSource(
                    QUrl.fromLocalFile(get_qml_full_path("web_debug_qt6.qml"))
                )
            else:
                self.view.setSource(
                    QUrl.fromLocalFile(get_qml_full_path("web_debug.qml"))
                )
        else:
            title = self.TITLE
            self.view.setInitialProperties(dict(view_props, debugMode=debug_log_html))
            if isQt6():
                self.view.setSource(
                    QUrl.fromLocalFile(get_qml_full_path("web_qt6.qml"))
                )
            else:
                self.view.setSource(QUrl.fromLocalFile(get_qml_full_path("web.qml")))

        errors = [e.toString() for e in self.view.errors()]
        expected_errors = [
            e for e in errors if "has already been used for type registration" in e
        ]
        qml_deps_need_restart = not self.view.rootObject() or (
            errors and len(expected_errors) == len(errors)
        )
        if qml_deps_need_restart:
            show_msg_bar_info("Please restart QGIS for changes to take effect")
        if errors and len(expected_errors) < len(errors):
            raise QmlError(errors)

        self.view.setTitle(title)
        self.profilePath = self.view.rootObject().getProfilePath()

        # Connect closing signal
        self.view.closing.connect(self._on_closed)
        if logout_and_reload:
            self.view.closing.connect(self.cleanup)

        self.view.setModality(Qt.WindowModality.ApplicationModal)
        self.view.show()

        return self.view

    def logout(self):
        """Logout HERE Platform"""
        self.view.rootObject().logout()

    def cleanup(self):
        """Cleanup WebEngine data directory"""
        if self.view:
            if not self.profilePath:
                self.profilePath = self.view.rootObject().getProfilePath()
            self.view.deleteLater()
            self.view = None
        if self.profilePath:
            shutil.rmtree(self.profilePath, ignore_errors=True)
        for entry in os.scandir(os.path.dirname(self.profilePath)):
            if entry.is_dir():
                shutil.rmtree(entry.path, ignore_errors=True)

    def _on_closed(self, *a):
        """Callback when the login window closes."""
        token_json = self.get_token_json()

        if token_json:
            set_sso_token_json(token_json)
            token = parse_sso_token_json(token_json)
            if token:
                print("Access token saved:", token)
                self.token = token
                self.login_finished.emit(True)
                return

        print("No access token retrieved:", token_json)
        self.token = None
        self.login_finished.emit(False)

    def get_token_json(self) -> str:
        """Extract token json response from QML root object."""
        if not self.view:
            return ""

        root = self.view.rootObject()
        if token_expired("refresh"):
            root.logoutAsync()
            clear_sso_token()
            print("refresh token expired")
            return ""
        if token_expired():
            print("token expired")
            return root.getTokenAgain()

        return root.getToken()
