###############################################################################
#
# Copyright (c) 2026 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os
import shutil

from ..config import TMP_DIR


def clear_tmp_directory() -> bool:
    if not os.path.exists(TMP_DIR):
        return False

    for item in os.listdir(TMP_DIR):
        item_path = os.path.join(TMP_DIR, item)

        if os.path.isfile(item_path) or os.path.islink(item_path):
            os.unlink(item_path)
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)

    return True
