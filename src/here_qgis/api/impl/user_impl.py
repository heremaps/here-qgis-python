###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from typing import Optional

from here_qgis.api.impl.base_api import APIResponseError, BaseApi


class UserBaseApi(BaseApi):
    """
    API implementation for user token generated from SSO login flow in HERE Platform
    """

    BASE_URL = "https://platform.here.com/api"

    def __init__(
        self,
        token: str,
        project_hrn: Optional[str] = None,
    ):
        """
        API init from user token generated from SSO login flow in HERE Platform
        """
        super().__init__(project_hrn)

        self.token = token
        self._user_id: Optional[str] = None

    def get_token(self) -> str:
        """
        Return non-scope token
        """
        return self.token

    def get_project_token(self) -> str:
        """
        Exchanges the current stored token for a new project-scoped access token.

        :return: accessToken string
        """
        url = f"{self.BASE_URL}/portal/scopedTokenExchange"
        payload = {"scope": self.project_hrn}

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        response = self.send_request("POST", url, headers=headers, payload=payload)
        data = response.json()

        if isinstance(data, dict) and "accessToken" in data:
            return data["accessToken"]
        else:
            raise APIResponseError("Invalid project-scoped token response")

    def get_user_id(self) -> Optional[str]:
        if self._user_id:
            return self._user_id

        self.get_info()
        return self._user_id

    def get_app_id(self) -> Optional[str]:
        return None

    def get_info(self) -> dict:
        response = self.send_request(
            "GET", "https://account.api.here.com/user/me/authorization"
        )
        data = response.json()
        self._caller_hrn = data["user"]["hrn"]
        self._realm = data["user"]["realm"]
        self._user_id = data["user"]["userId"]
        return data
