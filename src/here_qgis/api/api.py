###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os
from typing import Optional

import requests

from here_qgis.amplitude_events.amplitude_client import QgisAmplitude
from here_qgis.amplitude_events.api_event import APIEvent
from here_qgis.api.impl.app_impl import AppBaseApi
from here_qgis.api.impl.base_api import APIResponseError, BaseApi  # noqa
from here_qgis.api.impl.user_impl import UserBaseApi


class API:
    AMPLITUDE_EVENT_FACTORY = APIEvent

    def __init__(
        self,
        here_cred_path: Optional[str] = None,
        project_hrn: Optional[str] = None,
        token: Optional[str] = None,
    ):
        """Initializes the API with credentials.

        Examples:

            api = API("path/here_credentials.properties", project_hrn="...")

            api = API(token="some_token", project_hrn="...")
        """

        if not (here_cred_path or os.environ.get("HERE_CREDENTIALS_FILE") or token):
            raise ValueError("No HERE credentials path nor SSO login provided.")

        self._api_impl = self._api_impl_from_credential(
            here_cred_path=here_cred_path, token=token, project_hrn=project_hrn
        )
        self.project_hrn = project_hrn
        self.amplitude = QgisAmplitude()

    @classmethod
    def _api_impl_from_credential(
        cls,
        here_cred_path: Optional[str] = None,
        project_hrn: Optional[str] = None,
        token: Optional[str] = None,
    ) -> BaseApi:
        if token:
            return UserBaseApi(token, project_hrn)
        return AppBaseApi(here_cred_path, project_hrn)

    def get_token(self) -> Optional[str]:
        token = self._api_impl.get_token()
        return token

    def get_project_token(self) -> Optional[str]:
        return self._api_impl.get_project_token()

    def get_caller_hrn(self) -> str:
        return self._api_impl.get_caller_hrn()

    def get_caller_id(self) -> str:
        return self._api_impl.get_caller_id()

    def get_realm(self) -> str:
        return self._api_impl.get_realm()

    def _track_event(self, function_name: str):
        mm_event = self.AMPLITUDE_EVENT_FACTORY(
            user_id=self._api_impl.get_caller_id(),
            event_properties={"function": function_name},
        )
        self.amplitude.track(mm_event)

    def _send_request(
        self, method, url, headers=None, payload=None
    ) -> requests.Response:
        """Sends a request according to the input parameters"""
        return self._api_impl.send_request(method, url, headers, payload)

    def _send_request_with_project_scope(
        self, method, url, headers=None, payload=None
    ) -> requests.Response:
        """
        Sends a request according to the input parameters with project-scoped token
        """
        return self._api_impl.send_request_with_project_scope(
            method, url, headers, payload
        )
