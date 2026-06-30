###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import platform
from typing import Optional

from amplitude import BaseEvent


class QgisBaseEvent(BaseEvent):
    """Base Qgis event.

    Args:
        event_type (str): Name of an event
            (usually a class name, e.g. "mapmaking api event")
        user_id (str): User ID from credentials
        platform (str): Platform of the device
        os_name (str): Name of operating system
        os_version (str): Version of operating system
        event_properties(dict): Function that triggered an event, e.g.
            {"function": "fetch_catalogs"}
    """

    def __init__(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        event_properties: Optional[dict] = None,
    ):
        super().__init__(
            event_type=event_type,
            user_id=user_id,
            platform=platform.system(),
            os_name=platform.system(),
            os_version=platform.release() + "-" + platform.version(),
            event_properties=event_properties,
        )
