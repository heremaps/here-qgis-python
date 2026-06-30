# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.core import QgsDataSourceUri, QgsHttpHeaders


def uri_constructor(url, token):
    """
    Constructs URI based on the url, headers
    """

    uri = QgsDataSourceUri()
    uri.setParam("url", url)
    uri.setParam("type", "xyz")
    headers = QgsHttpHeaders({"Authorization": f"Bearer {token}"})
    uri.setHttpHeaders(headers)

    return bytes(uri.encodedUri()).decode("utf-8")
