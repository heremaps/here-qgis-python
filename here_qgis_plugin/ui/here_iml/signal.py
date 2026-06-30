###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.PyQt.QtCore import QObject, pyqtSignal


class PluginSignals(QObject):
    attribute_triggered = pyqtSignal()


# Create a global instance of PluginSignals
plugin_signals = PluginSignals()
