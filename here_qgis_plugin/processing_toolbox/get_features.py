###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from here_qgis.api.map import IMLBoundingBox, IMLMapApi

from ..api_factory import create_api_for_processing


def get_features(bbox, parameters, feedback, iml_context="default", query=""):
    # initiate the IMLApi

    here_cred_path = parameters.get("HERE_CREDENTIALS_FILE", "")
    iml_api = create_api_for_processing(
        IMLMapApi, here_cred_path, project_hrn=parameters["project_hrn"]
    )

    iml_bbox = IMLBoundingBox(**bbox)
    catalog_hrn = parameters["catalog_hrn"]
    layer_id = parameters["layer_id"]

    response = iml_api.get_features_by_bbox(
        catalog_hrn, layer_id, iml_bbox, iml_context, query
    )
    feedback.pushInfo(str(iml_bbox.get_bbox()))

    layer_feature, layer_name = response.get_features(), response.get_layer_name()
    layer_name += " " + iml_context.capitalize()

    return layer_feature, layer_name
