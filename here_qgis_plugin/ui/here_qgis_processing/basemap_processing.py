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


def basemap_tile_processing(
    styles, imageFormats, imageSizes, feature, langs, langs_sec, pview
):
    """Loads a HERE map tile using the selected settings."""
    params = {
        "HERE_CREDENTIALS_FILE": get_processing_here_cred_path_for_ui(),
        "styles": styles,
        "imageFormats": imageFormats,
        "imageSizes": imageSizes,
        "feature": feature,
        "langs": langs,
        "langs_sec": langs_sec,
        "pview": pview,
    }

    return processing.runAndLoadResults("here_qgis_processing:LoadBasemap", params)
