###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import configparser
from typing import Dict, Optional


class Credentials(Dict):
    def __init__(
        self,
        cred_properties: Optional[Dict] = None,
        token_info: Optional[Dict] = None,
    ):
        if not (cred_properties or token_info):
            raise ValueError("Provide credentials file or token file.")
        self.cred_properties = cred_properties
        self.token_info = token_info

    @classmethod
    def from_credentials_file(
        cls, cred_path: str, project_hrn: Optional[str] = None
    ) -> "Credentials":
        config = configparser.ConfigParser()
        # https://stackoverflow.com/questions/2885190/using-configparser-to-read-a-file-without-section-name # noqa
        with open(cred_path) as stream:
            cred = {}
            config.read_string("[top]\n" + stream.read())
            cred["user"] = config.get("top", "here.user.id")
            cred["client"] = config.get("top", "here.client.id")
            cred["access_key_id"] = config.get("top", "here.access.key.id")
            cred["access_key_secret"] = config.get("top", "here.access.key.secret")
            if config.has_option("top", "here.token.scope"):
                cred["scope"] = config.get("top", "here.token.scope")
            if project_hrn:
                cred["scope"] = project_hrn
            return Credentials(cred_properties=cred)
