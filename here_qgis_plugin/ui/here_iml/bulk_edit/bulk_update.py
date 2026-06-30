###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from here_qgis.api.here_utils import get_id_from_hrn
from here_qgis.api.mapmaking import MapMakingAPI


def bulk_update(
    credential_path: str,
    project_hrn: str,
    layer_id: str,
    map_type: str,
    data: dict,
):
    mm_api = MapMakingAPI(here_cred_path=credential_path, project_hrn=project_hrn)

    # TODO: separate function for next 3 lines
    # check where its used
    project_id = get_id_from_hrn(project_hrn)
    cached_response = mm_api.fetch_catalogs(project_id)
    catalog = cached_response.get_catalogs()[map_type]

    feature_collection = {
        "type": "FeatureCollection",
        "features": [{"id": feature_id, **feature} for feature_id, feature in data],
    }
    mm_api.patch_features(feature_collection, catalog, layer_id)
