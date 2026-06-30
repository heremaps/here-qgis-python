###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from typing import Optional

from here_qgis.amplitude_events.qgis_base_event import QgisBaseEvent


class MapmakingEvent(QgisBaseEvent):
    """Event for Mapmaking API.

    Args:
        user_id (str): User ID from credentials
        event_properties(dict): Function that triggered an event, e.g.
            {"function": "fetch_catalogs"}
    """

    def __init__(
        self,
        user_id: Optional[str] = None,
        event_properties: Optional[dict] = None,
    ):
        super().__init__(
            event_type="mapmaking api event",
            user_id=user_id,
            event_properties=event_properties,
        )
