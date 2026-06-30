###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from typing import List, Optional

from requests import HTTPError

from ..helper_functions import (
    map_project_hrn_2_project_hrn,
    project_hrn_2_map_project_hrn,
)
from .api import API
from .here_utils import get_id_from_hrn


class MemberRole:
    def __init__(self, memberHrn: str, role: str):
        self.memberHrn = memberHrn
        self.role = role


class Members:
    def __init__(self, response: dict):
        self.members: List[MemberRole] = []
        for item in response["items"]:
            member_hrn = item["memberHrn"]
            role = item["role"]
            self.members.append(MemberRole(member_hrn, role))

    def get_member_role(self, member_hrn):
        member_hrn = member_hrn or ""
        member_id = get_id_from_hrn(member_hrn)
        for member in self.members:
            if (
                member.memberHrn == member_hrn
                or get_id_from_hrn(member.memberHrn) == member_id
            ):
                return member.role
        return None


class MapProjectsAPI(API):
    def __init__(
        self,
        here_cred_path: Optional[str] = None,
        token: Optional[str] = None,
        project_hrn: Optional[str] = None,
        map_project_hrn: Optional[str] = None,
    ):
        if map_project_hrn and not project_hrn:
            project_hrn = map_project_hrn_2_project_hrn(map_project_hrn)
        super().__init__(
            here_cred_path,
            project_hrn=project_hrn,
            token=token,
        )
        if not (project_hrn or map_project_hrn):
            raise ValueError("Provide project_hrn or map_project_hrn")
        self.project_hrn = project_hrn
        self.map_project_hrn = map_project_hrn
        self.members = None

    def get_project_name(self):
        # just name, but maybe qhole response would be useful?
        headers = {"content-type": "application/json"}

        if self.map_project_hrn:
            map_project_hrn_to_url = self.map_project_hrn
        else:
            map_project_hrn_to_url = project_hrn_2_map_project_hrn(self.project_hrn)
        url = (
            "https://mapmaking.api.platform.here.com/v0/mapProjects/"
            f"{map_project_hrn_to_url}"
        )
        response = self._send_request_with_project_scope("GET", url, headers=headers)
        response = response.json()
        items = response.get("items", {})
        if items:
            return items[0]["configuration"]["name"]
        return ""

    def _get_admin_role_hrn(self):
        """
        Returns hrn of an ProjectAdmin role of project
        """
        headers = {"content-type": "application/json"}
        url = (
            "https://account.api.here.com/authorization/v1.1/roles?"
            f"roleName=ProjectAdmin&resource={self.project_hrn}"
        )
        response = self._send_request("GET", url, headers=headers)
        return response.json().get("data")[0].get("hrn", None).replace("/", "%2F")

    def _get_platform_project_permission(self):
        """
        Returns permission user have in project. When use in QGIS should always
        be used with self created with `create_api_for_ui`.
        When object is created with credentials and app is not added to the
        project it returns None.

        Returns:
        * "admin" if user has admin access to platform project
        * "reader" if user has reader access to platform project
        * 401 if token expired
        * None if user has not access to platform project
        """
        headers = {"content-type": "application/json"}
        admin_role_hrn = self._get_admin_role_hrn()
        url = (
            "https://account.api.here.com/authorization/v1.1/roles/"
            f"{admin_role_hrn}/entities"
        )

        response = self._send_request("GET", url, headers=headers)
        user_hrn = self.get_caller_hrn().split("/")[-1]
        for entry in response.json()["data"]:
            if entry["entityType"] == "user" and entry["info"]["userId"] == user_hrn:
                return "admin"

        # if 403 is returned it means user dont have read access to the project
        # otherwise, user has read access to the project
        url = (
            "https://account.api.here.com/authorization/v1.1/projects/"
            f"{self.project_hrn.replace('/', '%2F')}"
        )
        try:
            self._send_request("GET", url, headers=headers)
        except HTTPError as err:
            if err.response.status_code == 403:
                return None
            raise err
        return "reader"

    def _get_project_permission(self, member_hrn_or_id: Optional[str] = None):
        if not self.members:
            if not member_hrn_or_id:
                member_hrn_or_id = self.get_caller_hrn()
            headers = {"content-type": "application/json"}

            if self.map_project_hrn:
                map_project_hrn_to_url = self.map_project_hrn
            else:
                map_project_hrn_to_url = project_hrn_2_map_project_hrn(self.project_hrn)

            url = (
                "https://mapmaking.api.platform.here.com/v0/mapProjects/"
                f"{map_project_hrn_to_url}/members"
            )
            response = self._send_request("GET", url, headers=headers)
            self.members = Members(response.json())

        member_role = self.members.get_member_role(member_hrn_or_id)
        return member_role

    def has_edit_permission(self, member: Optional[str] = None) -> bool:
        role_mm = self._get_project_permission(member_hrn_or_id=member)
        role_platform = self._get_platform_project_permission()
        return role_mm == "editor" or role_mm == "admin" or role_platform == "admin"

    def has_read_permission(self, member: Optional[str] = None) -> bool:
        role_mm = self._get_project_permission(member_hrn_or_id=member)
        role_platform = self._get_platform_project_permission()
        return (
            role_mm == "reader"
            or role_mm == "editor"
            or role_mm == "admin"
            or role_platform == "admin"
            or role_platform == "reader"
        )
