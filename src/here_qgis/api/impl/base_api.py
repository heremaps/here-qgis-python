###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import json
from abc import abstractmethod
from typing import Optional

import requests


class BaseApi:
    """
    Base interface of API. Depends on input credential, API implementation
    for token generation and functions to get IML data will vary accordingly
    """

    def __init__(self, project_hrn: Optional[str] = None):
        self.project_hrn = project_hrn

        self._caller_hrn: Optional[str] = None
        self._realm: Optional[str] = None

    @abstractmethod
    def get_token(self) -> str:
        """
        Return non-scoped token
        """
        raise NotImplementedError()

    @abstractmethod
    def get_project_token(self) -> str:
        """
        Return project-scoped token
        """
        raise NotImplementedError()

    @abstractmethod
    def get_user_id(self) -> Optional[str]:
        """
        Return user id of input credential
        """
        raise NotImplementedError()

    @abstractmethod
    def get_app_id(self) -> Optional[str]:
        """
        Return app id of input credential
        """
        raise NotImplementedError()

    def get_caller_id(self) -> str:
        """
        Return caller id of input credential (app id or user id)
        """
        return self.get_app_id() or self.get_user_id()

    def get_caller_hrn(self) -> str:
        """
        Return caller hrn of input credential (app hrn or user hrn)
        """
        if self._caller_hrn:
            return self._caller_hrn
        realm = self.get_realm()
        app_id = self.get_app_id()
        if app_id:
            return f"hrn:here:account::{realm}:app/{app_id}"
        user_id = self.get_user_id()
        if user_id:
            return f"hrn:here:account::{realm}:user/{user_id}"

    @abstractmethod
    def get_info(self) -> dict:
        raise NotImplementedError()

    def get_realm(self) -> str:
        if self._realm:
            return self._realm
        if self.project_hrn:
            return self.realm_from_hrn(self.project_hrn)

        self.get_info()
        return self._realm

    @staticmethod
    def realm_from_hrn(hrn: str):
        """Extract realm from hrn, for example from project_hrn
        `hrn:here:authorization::realm-id:project/qgis-plugin-dev`
        """
        return hrn.split(":")[4]

    def send_request(
        self, method, url, headers=None, payload=None
    ) -> requests.Response:
        """Sends a request according to the input parameters

        :param str method: GET, POST, PUT, etc.
        :param str url: endpoint url
        :param dict headers: headers according to the request purpose
        :param dict payload: payload according to the request purpose

        :return: response requests.Response

        :raises: HTTPError
        """
        return self._send_request_with_token(
            method, url, headers, payload, token=self.get_token()
        )

    def send_request_with_project_scope(
        self, method, url, headers=None, payload=None
    ) -> requests.Response:
        """
        Sends a request according to the input parameters with project-scoped token
        """
        return self._send_request_with_token(
            method, url, headers, payload, token=self.get_project_token()
        )

    def _send_request_with_token(
        self, method, url, headers: dict = None, payload: dict = None, token: str = None
    ) -> requests.Response:
        """Sends a request according to the input parameters

        :param str method: GET, POST, PUT, etc.
        :param str url: endpoint url
        :param dict headers: headers according to the request purpose
        :param dict payload: payload according to the request purpose
        :param dict token: bearer token

        :return: response requests.Response

        :raises: HTTPError
        """

        headers = headers or {}
        if token:
            headers.update({"Authorization": f"Bearer {token}"})
        if payload:
            payload = json.dumps(payload)
        response: requests.Response = requests.request(
            method, url, headers=headers, data=payload
        )
        response.raise_for_status()

        return response


class APIResponseError(Exception):
    pass
