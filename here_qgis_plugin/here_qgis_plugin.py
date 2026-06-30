###############################################################################
#
# Copyright (c) 2023 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import logging

from qgis.core import QgsApplication
from qgis.gui import QgisInterface

from here_qgis.amplitude_events.amplitude_client import QgisAmplitude
from here_qgis.amplitude_events.install_event import InstallPluginEvent

# Import Processing Provider
from .here_qgis_provider import HereQgisPluginProvider
from .plugin_without_dependencies import PluginWithoutDependencies

# Import main plugin components
from .ui.here_iml.attribute.attribute import AttributeTable
from .ui.here_iml.attribute.attribute_all import AttributeTableAll
from .ui.here_iml.attribute.attribute_flatten import AttributeTableFlatten
from .ui.here_iml.authenticate.authentication import Authenticate
from .ui.here_iml.basemap.basemap import Basemap
from .ui.here_iml.bulk_edit.bulk_edit import BulkEditDialog
from .ui.here_iml.client_query.client_query_dialog import ClientIMLQuery
from .ui.here_iml.edit_map.edit_map import EditMapDialog
from .ui.here_iml.flatten_on_fly.flatten_on_fly import FlattenOnFly
from .ui.here_iml.imlmap.imlmaps import IMLMaps
from .ui.here_iml.mapmaking.mapmaking_project import MapmakingProjectLoad
from .ui.here_iml.property.property import PropertyList
from .ui.here_iml.reload_layer.reload_layer import ReloadLayers
from .ui.here_iml.settings.settings import SettingsDialog
from .ui.here_iml.upload_map.upload_map import UploadMapDialog

# Import utilities
from .ui.utils.required_plugin import plugin_checker
from .ui.utils.settings_manager import (
    clear_sso_token,
    get_already_installed,
    is_authenticated,
    is_valid_config_path,
    set_already_installed,
)
from .utils.dependencies import IsolatedDependencies

logger = logging.getLogger(__name__)


class HereQgisPlugin(PluginWithoutDependencies):
    """QGIS Plugin Implementation."""

    def __init__(self, iface: QgisInterface, deps: IsolatedDependencies):
        """Constructor."""
        super().__init__(iface)
        self.parent = self.iface.mainWindow()
        self.deps = deps
        if not get_already_installed():
            install_event = InstallPluginEvent()
            amplitude = QgisAmplitude()
            amplitude.track(install_event)
            set_already_installed()

    def initProcessing(self):
        """Initialize HERE Processing provider."""
        self.provider = HereQgisPluginProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        """Create the menu entries, toolbar icons, and Processing provider."""
        super().initGui()

        # Init Processing provider
        self.initProcessing()

        # Authentication Action
        self.auth_button.triggered.connect(self.run_auth)

        # Basemap Action
        self.basemap_button.triggered.connect(self.run_basemap)

        # IML Maps Action
        self.imlmap_button.triggered.connect(self.run_imlmap)

        # IML Maps Query Action
        self.query_button.triggered.connect(self.run_query)

        # IML Maps Settings Action
        self.settings_button.triggered.connect(self.run_settings)

        # Property Action
        self.property_button.triggered.connect(self.run_property)

        # Flatten on Fly Action
        self.flatten_fly_button.triggered.connect(self.run_flatten_on_fly)

        # Reload layers Action
        self.reload_layers_button.triggered.connect(self.run_reload_layers)

        # Upload Map Action
        self.upload_map_button.triggered.connect(self.run_upload_map)

        # Reload layers Action
        self.mapmaking_button.triggered.connect(self.run_mapmaking)

        # Edit Map Action
        self.edit_map_button.triggered.connect(self.run_edit_map)

        # Bulk Edit Action
        self.bulk_edit_button.triggered.connect(self.run_bulk_edit)

        # SSO Login Map Action
        self.login_button.triggered.connect(self.run_login)

        # SSO Logout Map Action
        self.logout_button.triggered.connect(self.run_logout)

        # Attribute Action selected feature
        self.attribute_button.triggered.connect(self.run_attribute)

        # Attribute Action all features
        self.attribute_all_button.triggered.connect(self.run_attribute_all)

        # Attribute Action flatten
        self.attribute_flatten_button.triggered.connect(self.run_attribute_flatten)

        self.refresh_button()

    def unload(self):
        """
        Unload plugin gracefully.

        + Remove toolbar, menu icons, Processing provider
        + Reset dependencies sys path.
        """
        super().unload()
        self.unload_processing()
        self.deps.unload()

    def unload_processing(self):
        """Remove HERE Processing provider."""
        try:
            QgsApplication.processingRegistry().removeProvider(self.provider)
        except RuntimeError as e:
            logger.warning(e)

    def disable_all_buttons(self):
        """Dont disable buttons when dependencies are valid"""
        ...

    def refresh_button(self, authenticated: bool = None):
        """Refresh UI button based on authenticate status"""
        if authenticated is None:
            authenticated = is_authenticated()

        config_valid = is_valid_config_path()

        # Enable/Disable buttons based on auth
        self.basemap_button.setEnabled(authenticated)
        self.imlmap_button.setEnabled(authenticated)
        self.property_button.setEnabled(authenticated)
        self.flatten_fly_button.setEnabled(authenticated)
        self.reload_layers_button.setEnabled(authenticated)
        self.upload_map_button.setEnabled(authenticated)
        self.mapmaking_button.setEnabled(authenticated)
        self.bulk_edit_button.setEnabled(authenticated)
        self.edit_map_button.setEnabled(authenticated)
        self.logout_button.setEnabled(authenticated)
        self.attribute_button.setEnabled(authenticated and config_valid)
        self.attribute_all_button.setEnabled(authenticated and config_valid)
        self.attribute_flatten_button.setEnabled(authenticated and config_valid)

    def run_auth(self):
        """Run Authentication."""
        # Refresh token and enable buttons
        self.refresh_button()

        if plugin_checker():
            auth_widget = Authenticate(self.parent)
            auth_widget.setWindowTitle("App credential")
            auth_widget.show()

            # Refresh token and enable buttons
            auth_widget.finished.connect(self.refresh_button)

    def run_basemap(self):
        """Run Basemap."""
        # Refresh token and enable buttons
        self.refresh_button()

        if plugin_checker() and is_authenticated():
            basemap_widget = Basemap(self.parent)
            basemap_widget.setWindowTitle("Map Tiles")
            basemap_widget.show()

    def run_imlmap(self):
        """Run IML Maps."""
        # Refresh token and enable buttons
        self.refresh_button()

        if plugin_checker() and is_authenticated():
            iml_map_widget = IMLMaps(self.parent)
            iml_map_widget.setWindowTitle("IML Maps")
            iml_map_widget.show()

    def run_property(self):
        """Run method for the property action."""
        # Refresh token and enable buttons
        self.refresh_button()

        if plugin_checker() and is_authenticated():
            property_widget = PropertyList(self.iface)
            property_widget.setWindowTitle("Property Mapping")
            property_widget.show()

    def run_attribute(self):
        """Run method for the attribute action."""
        # Refresh token and enable buttons
        self.refresh_button()

        if plugin_checker() and is_authenticated():
            attribute_widget = AttributeTable(self.iface)
            attribute_widget.setWindowTitle("Attribute Table")
            attribute_widget.show()

    def run_attribute_all(self):
        """Run method for the attribute action."""
        # Refresh token and enable buttons
        self.refresh_button()

        if plugin_checker() and is_authenticated():
            attribute_widget = AttributeTableAll(self.iface)
            attribute_widget.setWindowTitle("Attribute Table All")
            attribute_widget.show()

    def run_attribute_flatten(self):
        """Run method for the attribute flatten action."""
        # Refresh token and enable buttons
        self.refresh_button()

        if plugin_checker() and is_authenticated():
            # TODO: adjust to attribute_widget.show()
            # immediate delete in the constructor is an issue
            attribute_widget = AttributeTableFlatten(self.iface)
            attribute_widget.setWindowTitle("Attribute Table Flatten")
            # attribute_widget.exec_()

    def run_flatten_on_fly(self):
        """Run method for the run flatten on fly action."""
        # Refresh token and enable buttons
        self.refresh_button()

        if plugin_checker() and is_authenticated():
            attribute_widget = FlattenOnFly(self.iface)
            attribute_widget.setWindowTitle("Flatten on Fly")

    def run_reload_layers(self):
        """Run method for the run flatten on fly action."""
        # Refresh token and enable buttons
        self.refresh_button()

        if plugin_checker() and is_authenticated():
            reload_layers_obj = ReloadLayers(self.iface)
            reload_layers_obj.check_requirements()
            reload_layers_obj.reload_layers()
            reload_layers_obj.refresh_token()

    def run_upload_map(self):
        """Run method for the run upload map action."""
        # Refresh token and enable buttons
        self.refresh_button()

        if plugin_checker() and is_authenticated():
            attribute_widget = UploadMapDialog(self.iface)
            attribute_widget.setWindowTitle("Upload Map")
            attribute_widget.show()

    def run_mapmaking(self):
        """Run method for the run mapmaking action."""
        # Refresh token and enable buttons
        self.refresh_button()

        if plugin_checker() and is_authenticated():
            mapmaking_widget = MapmakingProjectLoad(self.parent)
            if mapmaking_widget.check_auth_status():
                mapmaking_widget.setWindowTitle("Mapmaking")
                mapmaking_widget.show()
            else:
                self.refresh_button(False)

    def run_edit_map(self):
        """Run method for the run edit map action."""
        # Refresh token and enable buttons
        self.refresh_button()

        if plugin_checker() and is_authenticated():
            dialog = EditMapDialog.try_create_dialog(
                self.iface.activeLayer(),
                self.parent,
            )
            if dialog:
                dialog.setWindowTitle("Single Edit")
                dialog.show()

    def run_bulk_edit(self):
        """Run method for the run bulk edit action."""
        # Refresh token and enable buttons
        self.refresh_button()

        if plugin_checker() and is_authenticated():
            dialog = BulkEditDialog.try_create_dialog(
                self.iface.activeLayer(),
                self.parent,
            )
            if dialog:
                dialog.setWindowTitle("Bulk Edit")
                dialog.show()

    def run_login(self):
        from .ui.here_iml.login.login import LoginDialog

        login_dialog = LoginDialog()
        # Connect signal before opening view
        login_dialog.login_finished.connect(self.refresh_button)

        login_dialog.create_qml_view()

        # login_dialog return view early, so must be stored to self
        self.login_dialog = login_dialog

    def run_logout(self):
        from .ui.here_iml.login.login import LoginDialog

        login_dialog = LoginDialog()
        # Connect signal before opening view
        login_dialog.login_finished.connect(lambda *a: clear_sso_token())
        login_dialog.login_finished.connect(self.refresh_button)

        login_dialog.create_qml_view(logout_and_close=True)

        self.login_dialog = login_dialog

    def run_query(self):
        """Run method for the query action."""
        # Refresh token and enable buttons
        self.refresh_button()

        if plugin_checker() and is_authenticated():
            query_widget = ClientIMLQuery.try_create_dialog(
                self.iface.activeLayer(), self.parent
            )
            if query_widget:
                query_widget.setWindowTitle("Query")
                query_widget.show()

    def run_settings(self):
        """Run method for the run settings action."""
        # Refresh token and enable buttons
        self.refresh_button()

        if plugin_checker() and is_authenticated():
            settings_widget = SettingsDialog(self.parent)
            settings_widget.setWindowTitle("Settings")
            settings_widget.show()
