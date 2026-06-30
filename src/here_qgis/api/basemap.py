###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from .api import API

# mapping to layer naming based on styles
layer_naming = {
    "explore.day": "HERE Explore Day",
    "lite.day": "HERE Lite Day",
    "logistics.day": "HERE Logistics Day",
    "explore.night": "HERE Explore Night",
    "lite.night": "HERE Lite Night",
    "explore.satellite.day": "HERE Explore Satellite Day",
    "lite.satellite.day": "HERE Lite Satellite Day",
    "satellite.day": "HERE Satellite Day",
    "topo.day": "HERE Lite Satellite Day",
}


class BasemapAPI(API):
    def generate_url(
        self, imageFormat, imageSize, style, feature, lang, lang_sec, pview
    ):
        """Generate url based on the inputs"""

        # url based on the input params
        url = (
            "https://maps.hereapi.com/v3/base/mc/xyz/"
            f"{imageFormat}?"
            f"size={imageSize}&"
            f"style={style}"
        )

        # feature
        if feature:
            url = f"{url}&features={feature}"
        # primary lang
        if lang:
            url = f"{url}&lang={lang}"
        # secondary lang
        if lang_sec:
            url = f"{url}&lang2={lang_sec}"
        # geopolitical view
        if pview:
            url = f"{url}&pview={pview}"
        # replace xyz
        url = url.replace("xyz", "{z}/{x}/{y}")

        return url
