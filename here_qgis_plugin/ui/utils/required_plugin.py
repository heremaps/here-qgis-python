###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


def plugin_checker():
    return True


# TODO: function not used - delete?
def _plugin_checker_old():
    from qgis.PyQt.QtWidgets import QMessageBox
    from qgis.utils import plugins

    required_plugin = "here_qgis_plugin"
    # or not plugins[required_plugin].isActive()
    # check the plugin exist
    if any(p.startswith(required_plugin) for p in plugins):
        mgs = QMessageBox()
        mgs.setIcon(QMessageBox.Icon.Warning)
        mgs.setWindowTitle("Missing Dependency")
        mgs.setText(f"The plugin '{required_plugin}' is required but is not installed")
        mgs.setInformativeText("Please install the required plugin to use this plugin.")
        mgs.setStandardButtons(QMessageBox.StandardButton.Ok)
        mgs.exec()
        return False
    else:
        return True
