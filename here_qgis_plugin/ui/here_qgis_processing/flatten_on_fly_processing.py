###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import processing


def flatten_on_fly_processing(layer):
    """Flattens the selected features on the fly."""

    params = {
        "layer": layer,
    }

    return processing.runAndLoadResults("here_qgis_processing:FlattenOnFly", params)
