###############################################################################
#
# Copyright (c) 2023 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################
import os
import time

from .. import config


def make_unique_full_path(ext="json"):
    return os.path.join(config.TMP_DIR, "%s.%s" % (time.time(), ext))


def make_unique_string(template: str = "{}{}", text: str = ""):
    return template.format(text, time.time())
