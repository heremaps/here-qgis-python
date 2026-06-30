###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from ...settings import UIToolbarsSetting


class Toolbars:
    KEY_DEV = UIToolbarsSetting.KEY_DEV
    KEY_MAPMAKING = UIToolbarsSetting.KEY_MAPMAKING

    def __init__(self, plugin_name):
        self.toolbars: dict = dict()
        self.default_key: str = self.KEY_DEV
        self.plugin_name: str = plugin_name

    def unload(self):
        for _key, toolbar in self.toolbars.items():
            # toolbar.clear()  # remove action from custom toolbar (toolbar still exist)
            toolbar.deleteLater()

    def _set_toolbar(self, key: str, toolbar):
        self.toolbars[key] = toolbar

    def get_dev_toolbar_name(self):
        return "{}: {}".format(self.plugin_name, self.KEY_DEV)

    def set_dev_toolbar(self, toolbar):
        self._set_toolbar(self.KEY_DEV, toolbar)

    def get_mapmaking_toolbar_name(self):
        return "{}: {}".format(self.plugin_name, self.KEY_MAPMAKING)

    def set_mapmaking_toolbar(self, toolbar):
        self._set_toolbar(self.KEY_MAPMAKING, toolbar)

    def refresh(self):
        self.set_default_key(UIToolbarsSetting.get_value(self.KEY_MAPMAKING))
        for key, toolbar in self.toolbars.items():
            enable = key == self.default_key
            toolbar.setVisible(enable)

    def set_default_key(self, default_key: str):
        if default_key in self.toolbars.keys():
            self.default_key = default_key
        else:
            raise RuntimeError("Invalid toolbar for key: '%s'" % default_key)

    def get_default_toolbar(self):
        return self.toolbars[self.default_key]
