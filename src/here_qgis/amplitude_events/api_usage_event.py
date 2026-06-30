###############################################################################
#
# Copyright (c) 2026 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from .qgis_base_event import QgisBaseEvent


class APIUsageEvent(QgisBaseEvent):
    """Event tracking API usage. From that event we can extract
    unique users IDs and track number of plugin users.
    This event is different from APIEvent - currently APIEvent tracking abilities are
    used only in MapmakingAPI. If in the future we will track other APIs,
    we can make use of APIEvent for that purpuse, but right now
    separate event is needed.

    Args:
        user_id (str): User ID from credentials
        event_properties(dict): Function that triggered an event, e.g.
            {"api_type": "UI"}
    """

    def __init__(
        self,
        user_id: str,
        event_properties: dict,
    ):
        super().__init__(
            user_id=user_id,
            event_type="API triggered",
            event_properties=event_properties,
        )
