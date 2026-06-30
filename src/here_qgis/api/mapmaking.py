###############################################################################
#
# Copyright (c) 2023 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import json
import time
from typing import List, Optional, Tuple

from here_qgis import MODULE_NAME_TAG
from here_qgis.amplitude_events.mapmaking_event import MapmakingEvent
from here_qgis.helper_functions import is_json_string

from .api import API


class MapMakingCachedResponse:
    def __init__(self, response, project_hrn_or_id):
        self.catalogs = {}
        project_lst = response.get("items", [])
        for project in project_lst:
            if project_hrn_or_id in project["projectHrn"]:
                self.catalogs = {
                    cat["format"]: cat["value"]["hrn"]
                    for cat in project["resources"]
                    if "hrn" in cat["value"]
                }
                self.catalogs["projectHrn"] = project["projectHrn"]
        if len(self.catalogs) == 0:
            raise Exception(f"Project {project_hrn_or_id} not found")

    def get_catalogs(self) -> dict:
        return self.catalogs


class LinkedProjects:
    def __init__(self, response: dict):
        self.response = response

    def _get_sorted_items(self) -> list:
        """Get sorted items by home relation"""
        return sorted(
            self.response.get("items", []),
            key=lambda item: item.get("relation", "") != "home",
        )

    def get_all_project_hrn(self) -> list:
        return [item.get("hrn") for item in self._get_sorted_items()]


class StatisticsCachedResponse:
    def __init__(self, response: dict):
        try:
            self.count = response["count"]["value"]
            self.byteSize = response["byteSize"]["value"]
            self.bbox = response["bbox"]["value"]
        except KeyError:
            raise Exception("Cannot create StatisticsCachedResponse object")

    def get_count(self):
        return self.count

    def get_byte_size(self):
        return self.byteSize

    def get_bbox(self):
        return self.bbox


class ViolationLayerFeature:
    def __init__(self, feature: dict):
        try:
            self.violation_id = feature["id"]
            self.references_id = []
            self.feature_types = []
            self.reference_names = []
            properties = feature["properties"]
            for ref in properties["references"]:
                self.references_id.append(ref["id"])
                self.feature_types.append(ref["featureType"])
                self.reference_names.append(ref["referenceName"])
            self.rule_id = properties["ruleId"]
            self.delta_change_state = properties["@ns:com:here:mom:delta"][
                "changeState"
            ]
            self.iso_country_code = properties["isoCountryCode"]
            self.rule_descr = properties["ruleDescription"]
            self.mom_type = feature["momType"]
        except KeyError as e:
            raise Exception(f"Cannot create ViolationLayerFeature object {e}")

    def get_violation_id(self):
        return self.violation_id

    def get_references_ids(self) -> list:
        return self.references_id

    def get_rule_id(self):
        return self.rule_id

    def get_delta_change_state(self):
        return self.delta_change_state

    def get_iso_country_code(self):
        return self.iso_country_code

    def get_rule_descr(self):
        return self.rule_descr

    def get_mom_type(self):
        return self.mom_type

    def get_feature_types(self):
        return self.feature_types

    def get_reference_names(self):
        return self.reference_names


class ViolationLayerCachedResponse:
    def __init__(self, response: dict):
        self.features: List[ViolationLayerFeature] = []
        try:
            for feature in response["features"]:
                self.features.append(ViolationLayerFeature(feature))
        except Exception as e:
            raise Exception(f"Cannot create ViolationLayerCachedResponse object: {e}")

    def get_features(self):
        return self.features


class MapMakingAPI(API):
    AMPLITUDE_EVENT_FACTORY = MapmakingEvent

    def __init__(
        self,
        here_cred_path: Optional[str] = None,
        project_hrn: Optional[str] = None,
        token: Optional[str] = None,
    ):
        super().__init__(
            here_cred_path=here_cred_path, project_hrn=project_hrn, token=token
        )
        self.next_actions = {}
        self.operation_states = {}

    def get_all_linked_project_hrn(self, catalog_hrn) -> List[str]:
        """Get linked project hrn of a given catalog hrn
        :param: str catalog_hrn: catalog hrn
        :returns: project_hrn

        """
        api_url = (
            "https://account.api.here.com/authorization/v1.1/resources/"
            f"{catalog_hrn}/projects"
        )
        response = self._send_request("GET", api_url)
        data = response.json()
        return LinkedProjects(data).get_all_project_hrn()

    def fetch_catalogs(self, project_hrn_or_id: str = "") -> MapMakingCachedResponse:
        """Fetch catalogs based on the project HRN or ID
        :param: str project_hrn_or_id: Project HRN or ID

        :raises:
            Exception: if Project ID not found

        :returns: MapMakingCachedResponse object
        """
        project_url = "https://mapmaking.api.platform.here.com/v0/mapProjects"
        if self.project_hrn and project_hrn_or_id in self.project_hrn:
            response = self._send_request_with_project_scope("GET", project_url)
        else:
            response = self._send_request("GET", project_url)

        self._track_event("fetch_catalogs")

        return MapMakingCachedResponse(response.json(), project_hrn_or_id)

    def patch_features(self, data: dict, catalog: str, layer_id: str) -> dict:
        """Patches an existing feature.

        :param dict data: data to be uploaded. Provide only those fields that
        you want to update.

        :param str catalog: input or livemap catalog_hrn

        :param str layer_id: layer id that data should be uploaded into

        :return: response as dict

        :raises: Exception
        """
        headers = {"content-type": "application/geo+json"}
        url = self.build_interactive_api_url(
            catalog,
            layer_id,
            "features",
            ne="retain",
            e="patch",
            transactional="true",
        )

        # if "properties" not in data:
        #     data["properties"] = {}
        self._add_delta_to_feature_collection(data)

        response = self._send_request_with_project_scope(
            "POST",
            url,
            headers=headers,
            payload=data,
        )
        return response.json()

    def upload_data(self, data: dict, catalog: str, layer_id: str) -> dict:
        """Uploads data to input or livemap catalogs with specified.
        It expects MOM structure as the input.

        :param dict data: data to be uploaded

        :param str catalog: input or livemap catalog_hrn (fetched automatically)

        :param str layer_id: layer id that data shoud be uploaded into

        :return: response as dict

        :raises:
            Exception: if inserted/updated not in response
        """
        headers = {"content-type": "application/geo+json"}
        # main URL
        url = self.build_interactive_api_url(catalog, layer_id, "features")
        # process data appropriate to the URL
        data = self.process_data(data)
        self.validate_data(data)

        response = self._send_request_with_project_scope(
            "PUT", url, headers=headers, payload=data
        )
        response = response.json()

        self._track_event("upload_data")

        return response

    def upload_edited_data(self, data: dict, catalog: str, layer_id: str) -> dict:
        """Uploads edited data to MapMaking.
        It expects MOM structure as the input.

        :param dict data: data to be uploaded

        :param str catalog: input or livemap catalog_hrn (fetched automatically)

        :param str layer_id: layer id that data shoudl be uploaded into

        :return: response as dict

        :raises:
            Exception: if inserted/updated not in response
        """
        return self.upload_data(
            self._add_delta_to_feature_collection(data), catalog, layer_id
        )

    def build_interactive_api_url(
        self,
        catalog_hrn: str,
        layer_id: str,
        endpoint: str,
        include_sent_with=True,
        **kwargs,
    ) -> str:
        """
        Returns url in form:
        `https://interactive.data.api.platform.here.com/interactive/v1/
        catalogs/{catalog_hrn}/layers/{layer_id}/{endpoint}?kwargs`

        :example usage:

        `self.build_interactive_api_url(
            "some_hrn", "place", "features", last_param="some_hrn:123" id="id1,id2"
        )`

        result: `https://interactive.data.api.platform.here.com/interactive/v1
        /catalogs/some_hrn/layers/place/features?id=id1,id2?sentWith={MODULE_NAME_TAG}`
        """
        url = (
            "https://interactive.data.api.platform.here.com/interactive/v1"
            f"/catalogs/{catalog_hrn}"
            f"/layers/{layer_id}/{endpoint}"
        )
        separator = "?"
        for key, value in kwargs.items():
            url += f"{separator}{key}={value}"
            separator = "&"
        if include_sent_with:
            url += f"{separator}sentWith={MODULE_NAME_TAG}"
        return url

    def get_input_catalog_hrn(self, project_id: str):
        if self.input_catalog_hrn == "":
            catalogs = self.fetch_catalogs(project_id)
            self.input_catalog_hrn = catalogs.get_catalogs()["input"]

    def get_statistics(self, catalog_hrn, layer_id) -> StatisticsCachedResponse:
        """Returns StatisticsCachedResponse

        :param str catalog_hrn: catalog hrn

        :param str layer_id: Id of layer

        :return: StatisticsCachedResponse
        """
        headers = {"content-type": "application/json"}
        url = self.build_interactive_api_url(catalog_hrn, layer_id, "statistics")
        response = self._send_request("GET", url, headers=headers)
        return StatisticsCachedResponse(response.json())

    def get_violation_layer(
        self, catalog_hrn: str, layer_id: str
    ) -> ViolationLayerCachedResponse:
        """Returns ViolationLayerCachedResponse

        :param str catalog_hrn: catalog hrn

        :param str layer_id: Id of layer you want to get violation, e.g. "place"

        :return: ViolationLayerCachedResponse
        """
        headers = {"content-type": "application/geo+json"}
        url = self.build_interactive_api_url(
            catalog_hrn, f"{layer_id}-violation", "search"
        )
        response = self._send_request("GET", url, headers=headers)
        return ViolationLayerCachedResponse(response.json())

    def delete_features(self, catalog_hrn: str, layer_id: str, ids: list) -> bool:
        ids = ",".join(ids)
        headers = {"content-type": "application/x-empty"}
        url = self.build_interactive_api_url(
            catalog_hrn, layer_id, "features", False, id=ids
        )
        response = self._send_request("DELETE", url, headers=headers)
        if response.status_code == 204:
            return True
        return False

    def validate_data(self, data):
        if isinstance(data, dict):
            features = data.get("features", list())
            if isinstance(features, list) and len(features):
                return True
        raise ValueError("Invalid or empty data payload.")

    def process_data(self, data) -> dict:
        """processes the data from QgsVectorLayer suitable for MapMaking API

        :param dict data: data to process

        :return dict

        """

        def _process_prop(key, value):
            if key == "fid":
                return None
            if value == "NaN":
                return key, None

            if is_json_string(value):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError as e:
                    raise e
            return key, value

        def _process(feature: dict):
            return dict(
                feature,
                properties=dict(
                    filter(
                        None,
                        (_process_prop(k, v) for k, v in feature["properties"].items()),
                    )
                ),
            )

        features = [_process(feature) for feature in data["features"]]
        # Add missing structure
        processed_data = {"type": "FeatureCollection", "features": features}
        return processed_data

    def _add_delta(self, feature: dict):
        """Adds delta to feature"""
        delta = dict()
        delta["changeState"] = "UPDATED"
        delta["reviewState"] = "PENDING"
        feature["properties"]["@ns:com:here:mom:delta"] = delta

    def _add_delta_to_feature_collection(self, data: dict) -> dict:
        """Adds delta to each feature in FeatureCollection."""
        for feature in data["features"]:
            self._add_delta(feature)
        return data

    def ondemand_process(self, operations):
        """
        Executes on-demand processes
        :param operations: List of tuples (operation, configuration)
        """
        for operation, configuration in operations:
            url = (
                "https://mapmaking.api.platform.here.com/v0"
                f"/operations/{operation}/activate"
            )
            payload = {
                "operation": operation,
                "mode": "onDemand",
                "configuration": configuration,
            }
            try:
                response = self._send_request(
                    "POST",
                    url,
                    headers={"Content-Type": "application/json"},
                    payload=payload,
                )
                response = response.json()

                self._track_event("ondemand_process")
                # store states
                self.next_actions[operation] = response["state"]
            except Exception as e:
                print(f"Error during operation activation {e}, {operation}")
                self.next_actions[operation] = "failed"

    def check_operation_states(self) -> Tuple[dict, dict]:
        """Checks the states of activated operations till their finish

        :returns tuple[dict, dict]:
            First dict with `nextActions` fields
            from response (indicates if processes finished). Second dict with `state`
            fields from reponse (indicates in what state processes finished).
        """
        url = "https://mapmaking.api.platform.here.com/v0/operations"
        while not list(self.next_actions.values()) == len(self.next_actions) * [
            "activate"
        ]:
            operations = self._send_request("GET", url)
            operations = operations.json()
            self._track_event("check_operation_states")
            items = operations.get("items", [])
            for item in items:
                operation = item.get("operation")
                if operation in self.next_actions.keys():
                    next_actions = item.get("nextActions")
                    state = item.get("state")
                    if next_actions and state:
                        self.next_actions[operation] = next_actions[0]
                        self.operation_states[operation] = state
            time.sleep(10)
        return self.next_actions, self.operation_states

    def fetch_map_projects(self):
        """Fetches map projects from HERE Mapmaking API.

        Returns:
            list: Filtered list of map project items where baseMapSource is not None.
        Raises:
            requests.exceptions.RequestException: If the HTTP request fails.
        """
        url = "https://mapmaking.api.platform.here.com/v0/mapProjects"
        data = self._send_request("GET", url)
        data = data.json()
        items = data.get("items", [])
        return [
            item
            for item in items
            if item.get("configuration", {}).get("baseMapSource") not in [None, "none"]
        ]
