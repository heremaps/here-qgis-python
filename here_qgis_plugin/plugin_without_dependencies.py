###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os.path
from typing import List

from qgis.core import Qgis
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QCoreApplication, QLocale, QSettings, QTranslator
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMenu, QToolButton

from . import config

# Import main plugin components
from .ui.here_iml.toolbars import Toolbars
from .ui.icons import (
    icon_attribute_all,
    icon_attribute_flatten,
    icon_attribute_table,
    icon_edit_here,
    icon_iml_map,
    icon_logo,
    icon_maptile_here,
    icon_project_list_here,
    icon_property_mapping,
    icon_reload_here,
    icon_signin_here,
    icon_signout_here,
)


class PluginWithoutDependencies:
    """QGIS Plugin Implementation."""

    def __init__(self, iface: QgisInterface):
        """Constructor."""
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.provider = None  # For Processing Provider
        self.actions = []
        self.menu = QMenu(self.tr(f"&{config.PLUGIN_NAME}"))

        # Initialize locale
        overrideLocale = QSettings().value("locale/overrideFlag", "")
        if overrideLocale != "true":
            locale = QLocale.system().name()[:2]
        else:
            locale = QSettings().value("locale/userLocale", "")[:2]
        locale_path = os.path.join(
            self.plugin_dir, "i18n", f"HereQgisPlugin{locale}.qm"
        )

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

    def tr(self, message):
        """Get the translation for a string using Qt translation API."""
        return QCoreApplication.translate("HereQgisPlugin", message)

    def create_qaction(
        self,
        *qaction_args,
        enabled_flag=True,
        status_tip=None,
        whats_this=None,
        parent=None,
    ):
        """Add a toolbar icon to the toolbar."""
        n_args = len(qaction_args)
        if n_args == 1:
            (text,) = qaction_args
            action = QAction(text, parent)
        elif n_args == 2:
            icon, text = qaction_args
            action = QAction(icon, text, parent)
        else:
            raise ValueError(
                "Invalid arguments for QAction: {}".format(n_args), qaction_args
            )

        action.setEnabled(enabled_flag)

        status_tip = status_tip or text
        whats_this = whats_this or text

        action.setStatusTip(status_tip)
        action.setWhatsThis(whats_this)

        return action

    def create_tool_button(self, qactions: List[QAction]):
        button_menu = QMenu()
        for action in qactions:
            button_menu.addAction(action)

        tool_button = QToolButton()
        tool_button.setMenu(button_menu)
        tool_button.setDefaultAction(qactions[0])
        tool_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)

        return tool_button

    def disable_all_buttons(self):
        """Disable all buttons due to dependencies issue"""
        # Log visually
        self.iface.messageBar().pushMessage(
            (
                f"{config.PLUGIN_NAME} is disabled due to errors when installing"
                " dependencies. Please try to restart QGIS after installation"
            ),
            level=Qgis.MessageLevel.Critical,
            duration=5,
        )
        # Disable plugin actions
        for action in self.get_all_actions():
            action.setEnabled(False)
            action.setToolTip("Plugin disabled due to missing dependencies")

    def get_all_actions(self):
        """Return a flat list of all QAction objects from self.actions."""

        def _iter(actions: list):
            for item in actions:
                if isinstance(item, QAction):
                    yield item
                elif isinstance(item, list):
                    yield from _iter(item)

        return list(_iter(self.actions))

    def initGui(self):
        """Create the menu entries, toolbar icons, and Processing provider."""

        # Authentication Action
        self.auth_button = self.create_qaction(
            # QIcon(icon_signin_here),
            self.tr("App credential"),
        )

        # Basemap Action
        self.basemap_button = self.create_qaction(
            QIcon(icon_maptile_here), self.tr("Map Tiles")
        )

        # IML Maps Action
        self.imlmap_button = self.create_qaction(
            QIcon(icon_iml_map), self.tr("IML Maps")
        )

        # Property Action
        self.property_button = self.create_qaction(
            QIcon(icon_property_mapping),
            self.tr("Property Mapping"),
        )

        # Flatten on Fly Action
        self.flatten_fly_button = self.create_qaction(
            self.tr("Flatten on Fly"),
        )

        # Reload layers Action
        self.reload_layers_button = self.create_qaction(
            QIcon(icon_reload_here),
            self.tr("Reload Layers"),
        )

        # Upload Map Action
        self.upload_map_button = self.create_qaction(
            self.tr("Upload Map"),
        )
        # Reload layers Action
        self.mapmaking_button = self.create_qaction(
            QIcon(icon_project_list_here),
            self.tr("MapMaking"),
        )
        # Edit Map Action
        self.edit_map_button = self.create_qaction(
            self.tr("Single Edit"),
        )
        # Bulk Edit Action
        self.bulk_edit_button = self.create_qaction(
            QIcon(icon_edit_here),
            self.tr("Bulk Edit"),
        )

        # SSO Login Map Action
        self.login_button = self.create_qaction(
            QIcon(icon_signin_here),
            self.tr("Login"),
        )

        # SSO Logout Map Action
        self.logout_button = self.create_qaction(
            QIcon(icon_signout_here),
            self.tr("Logout"),
        )

        # Attribute Action selected feature
        self.attribute_button = self.create_qaction(
            QIcon(icon_attribute_table),
            self.tr("Attribute"),
        )

        # Attribute Action all features
        self.attribute_all_button = self.create_qaction(
            QIcon(icon_attribute_all),
            self.tr("Attribute All"),
        )

        # Attribute Action flatten
        self.attribute_flatten_button = self.create_qaction(
            QIcon(icon_attribute_flatten),
            self.tr("Attribute Flatten"),
        )

        # Query Action
        self.query_button = self.create_qaction(
            self.tr("Query"),
        )

        # Settings Action
        self.settings_button = self.create_qaction(
            self.tr("Settings"),
        )

        # Custom toolbar
        self.toolbars = Toolbars(config.PLUGIN_NAME)

        toolbar = self.iface.addToolBar(self.toolbars.get_dev_toolbar_name())

        self.actions = [
            [
                self.login_button,
                self.logout_button,
                self.auth_button,
            ],
            "MapMaking",
            self.basemap_button,
            self.mapmaking_button,
            self.reload_layers_button,
            self.bulk_edit_button,
            "Others",
            self.imlmap_button,
            self.property_button,
            self.flatten_fly_button,
            self.upload_map_button,
            self.edit_map_button,
            [
                self.attribute_button,
                self.attribute_all_button,
                self.attribute_flatten_button,
            ],
            self.query_button,
            self.settings_button,
        ]

        for item in self.actions:
            if isinstance(item, list):
                toolbar.addWidget(self.create_tool_button(item))
            elif isinstance(item, QAction):
                toolbar.addAction(item)
            elif isinstance(item, str):
                ...
            else:
                raise ValueError("actions item invalid: {}".format(repr(item)))

        self.toolbars.set_dev_toolbar(toolbar)

        toolbar_mm = self.iface.addToolBar(self.toolbars.get_mapmaking_toolbar_name())

        for item in [
            [
                self.login_button,
                self.logout_button,
                self.auth_button,
            ],
            self.basemap_button,
            self.mapmaking_button,
            self.reload_layers_button,
            self.bulk_edit_button,
        ]:
            if isinstance(item, QAction):
                toolbar_mm.addAction(item)
            elif isinstance(item, list):
                toolbar_mm.addWidget(self.create_tool_button(item))

        self.toolbars.set_mapmaking_toolbar(toolbar_mm)
        self.toolbars.refresh()

        self.init_menu()

        self.disable_all_buttons()

    def init_menu(self):
        menu = self.menu
        menu.setIcon(QIcon(icon_logo))
        for item in self.actions:
            if isinstance(item, list):
                # sublist of actions into section
                if isinstance(item[0], str):
                    menu.addSection(item[0])
                else:
                    menu.addSection(item[0].text())
                for action in item:
                    menu.addAction(action)
                # menu.addSeparator()
            elif isinstance(item, QAction):
                menu.addAction(item)
            elif isinstance(item, str):
                menu.addSection(item)
            else:
                raise ValueError("actions item invalid: {}".format(repr(item)))
        # add web menu (alphabetical order)
        self.iface.addPluginToWebMenu("_tmp", self.login_button)

        web_menu = self.iface.webMenu()

        title_lc = menu.title().replace("&", "").lower()
        for action in web_menu.actions():
            lc = action.text().replace("&", "").lower()
            # print(title_lc, lc, title_lc < lc)  # debug
            if title_lc < lc:
                web_menu.insertMenu(action, menu)
                break
        else:
            web_menu.addMenu(menu)

        self.iface.removePluginWebMenu("_tmp", self.login_button)

    def unload(self):
        """
        Unload plugin gracefully.

        + Remove toolbar, menu icons, Processing provider
        + Reset dependencies sys path.
        """
        self.iface.webMenu().removeAction(self.menu.menuAction())
        self.toolbars.unload()
