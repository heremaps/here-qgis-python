###############################################################################
#
# Copyright (c) 2026 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from .qgis_base_event import QgisBaseEvent


class InstallPluginEvent(QgisBaseEvent):
    "Event tracking plugin installation."

    def __init__(
        self,
        # This may be use if we want track updating plugin
        # event_properties: Optional[dict] = None
    ):
        super().__init__(
            # During installation it's impossible to get user ID
            user_id="Anonymous_User",
            event_type="plugin installed",
            event_properties={"installation_type": "first"},
        )
