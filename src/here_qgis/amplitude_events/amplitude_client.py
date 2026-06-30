###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from typing import Optional

from amplitude import Amplitude, BaseEvent, Config

from here_qgis.amplitude_events.amplitude_config import AMPLITUDE_CONFIG


class QgisAmplitude(Amplitude):
    """Wrapper for amplitude.Amplitude client"""

    def __init__(self, configuration: Optional[Config] = AMPLITUDE_CONFIG):
        super().__init__(configuration.api_key, configuration)

    def is_tracking_enabled(self):
        """Returns true if tracking is enabled"""
        return self.configuration.api_key and not self.configuration.opt_out

    def track(self, event: BaseEvent):
        """Wrapper for amplitude.Amplitude.track(event) function.
        Calls super().track(event) if tracking is enabled.
        """
        if self.is_tracking_enabled():
            try:
                super().track(event)
            except Exception as e:
                self.configuration.logger.warning(f"Cannot track event: {e}")
