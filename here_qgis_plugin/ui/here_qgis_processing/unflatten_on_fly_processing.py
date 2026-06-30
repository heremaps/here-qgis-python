###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import processing


def unflatten_on_fly_processing(layer, unflatten_selected=False):
    """Unflattens the selected features on the fly."""

    params = {
        "layer_id": layer,
        "unflatten_selected": unflatten_selected,
    }

    return processing.runAndLoadResults(
        "here_qgis_processing:IMLUnflattenOnTheFly", params
    )
