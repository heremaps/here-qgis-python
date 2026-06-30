###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from typing import Optional

import requests
from requests_oauthlib import OAuth1

from .platform_credentials import Credentials


class PlatformAuth:
    url = "https://account.api.here.com/oauth2/token"

    def __init__(self, credentials: Credentials, project_hrn: Optional[str] = None):
        self.token_info = {}
        self.cred_properties = {}
        if credentials.token_info:
            self.token_info = credentials.token_info
        if credentials.cred_properties:
            self.cred_properties = credentials.cred_properties
        self.project_hrn = project_hrn

    @property
    def token(self):
        if not self.token_info:
            self.get_token()
        return self.token_info["access_token"]

    def get_token(self):
        oauth = OAuth1(
            self.cred_properties["access_key_id"],
            client_secret=self.cred_properties["access_key_secret"],
            signature_method="HMAC-SHA256",
        )
        query = {"grant_type": "client_credentials"}
        if "scope" in self.cred_properties:
            query["scope"] = self.cred_properties["scope"]
        if self.project_hrn:
            query["scope"] = self.project_hrn

        resp = requests.request(
            "POST",
            self.url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=query,
            auth=oauth,
        )
        resp.raise_for_status()

        self.token_info = resp.json()
