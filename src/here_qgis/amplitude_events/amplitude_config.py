###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os

from amplitude import Config

from here_qgis import MODULE_ID, deobfuscate_string

DEFAULT_AMPLITUDE_API_KEY = ""
DEFAULT_ALLOW_AMPLITUDE = ""

AMPLITUDE_API_KEY = deobfuscate_string(DEFAULT_AMPLITUDE_API_KEY, MODULE_ID)
ALLOW_AMPLITUDE = os.environ.get("ALLOW_AMPLITUDE", DEFAULT_ALLOW_AMPLITUDE)

AMPLITUDE_CONFIG = Config(AMPLITUDE_API_KEY)

if ALLOW_AMPLITUDE == "allow":
    AMPLITUDE_CONFIG.logger.info("Amplitude tracking enabled")
else:
    AMPLITUDE_CONFIG.opt_out = True
    AMPLITUDE_CONFIG.logger.info("Amplitude tracking disabled")
