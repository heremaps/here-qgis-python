###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import processing

from ...api_factory import get_processing_here_cred_path_for_ui


def upload_mapmaking_processing(
    upload_layer,
    project_hrn,
    layer_id,
    map_type,
    upload_selected_only=False,
    upload_edited=False,
):
    """Uploads the selected layer to HERE Mapmaking."""
    params = {
        "HERE_CREDENTIALS_FILE": get_processing_here_cred_path_for_ui(),
        "project_hrn": project_hrn,
        "layer_id": layer_id,
        "map_type": map_type,
        "upload_layer": upload_layer,
        "upload_selected_only": upload_selected_only,
        "upload_edited": upload_edited,
    }

    return processing.runAndLoadResults("here_qgis_processing:MapMakingUpload", params)
