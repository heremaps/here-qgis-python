###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os
from typing import Optional

from here_qgis.api.impl.base_api import BaseApi
from here_qgis.platform.platform_auth import PlatformAuth
from here_qgis.platform.platform_credentials import Credentials


class AppBaseApi(BaseApi):
    """
    API implementation for app credential properties file downloaded from HERE Platform.
    """

    def __init__(
        self,
        here_cred_path: Optional[str] = None,
        project_hrn: Optional[str] = None,
    ):
        """Initializes the API with credentials."""
        super().__init__(project_hrn)

        HERE_CREDENTIALS_FILE = here_cred_path or os.environ.get(
            "HERE_CREDENTIALS_FILE"
        )

        if not HERE_CREDENTIALS_FILE or not os.path.exists(HERE_CREDENTIALS_FILE):
            raise ValueError(
                "No HERE credentials path provided nor environment variable set."
            )

        platform_cred = Credentials.from_credentials_file(HERE_CREDENTIALS_FILE)

        if platform_cred is None:
            raise ValueError("Failed to load platform credentials from the given file.")

        self.platform_cred = platform_cred
        self.platform = PlatformAuth(self.platform_cred)
        self.platform_project = PlatformAuth(
            self.platform_cred, project_hrn=project_hrn
        )

        self._app_id: Optional[str] = None
        self._app_name: Optional[str] = None
        self._app_status: Optional[str] = None

    def get_token(self) -> str:
        if self.platform is None:
            raise RuntimeError("Platform or authentication not initialized properly.")
        return self.platform.token

    def get_project_token(self) -> str:
        if self.platform_project is None:
            raise RuntimeError("Platform or authentication not initialized properly.")
        return self.platform_project.token

    def get_user_id(self) -> Optional[str]:
        return self.platform_cred.cred_properties["user"]

    def get_app_id(self) -> Optional[str]:
        return self.platform_cred.cred_properties["client"]

    def get_info(self) -> dict:
        response = self.send_request(
            "GET", "https://account.api.here.com/app/me/authorization"
        )
        data = response.json()
        self._caller_hrn = data["app"]["hrn"]
        self._realm = data["app"]["realm"]
        self._app_id = data["app"]["clientId"]
        self._app_name = data["app"]["name"]
        self._app_status = data["app"]["status"]
        return data
