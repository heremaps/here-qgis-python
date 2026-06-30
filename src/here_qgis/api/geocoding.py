###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import re
from typing import List

from .api import API, APIResponseError


class GeocodeObj:
    def __init__(self, hrn_id: str, result_type: str, position: dict, address: dict):
        """
        Creates GeocodeObj from reponse entry.
        """
        self.hrn_id = hrn_id
        self.result_type = result_type
        self.position = position
        self.address = address

    def get_hrn_id(self):
        return self.hrn_id

    def get_result_type(self):
        return self.result_type

    def get_position(self):
        return self.position

    def get_address(self):
        return self.address

    def get_longitude(self):
        return self.position["lng"]

    def get_latitude(self):
        return self.position["lat"]


class GeocodeCachedResponse:
    def __init__(self, response: dict):
        """
        Cached geocode api response object
        :raises: GeocodeCachedResponseError
        """
        self.results: List[GeocodeObj] = []
        if response["items"]:
            for item in response["items"]:
                try:
                    hrn_id = item["id"]
                    result_type = item["resultType"]
                    position = item["position"]
                    address = item["address"]
                except KeyError:
                    raise GeocodeCachedResponseError("Structure changed")
                # TODO: in documentation there is no `categories` field
                # I'll keep it commented for now
                # if "categories" in item:
                #     temp_dict.update(item["categories"][0])
                self.results.append(
                    GeocodeObj(
                        hrn_id=hrn_id,
                        result_type=result_type,
                        position=position,
                        address=address,
                    )
                )

    def get_geocode_objects(self) -> List[GeocodeObj]:
        return self.results

    def is_empty(self):
        """ "
        Check if 'items' array of response was empty.
        """
        return len(self.results) == 0


class GeocodeCachedResponseError(APIResponseError):
    def __init__(self, message, prefix="Cannot parse geocode API response"):
        super().__init__(f"{prefix}: {message}")


class GeocodeAPI(API):
    def geocode_request(self, address_string: str) -> GeocodeCachedResponse:
        """
        Geocode by the address string

        return: cached response as GeocodeCachedResponse
        """
        address = re.sub("[^a-zA-Z0-9]", "+", address_string)

        geocode_api_url = (
            f"https://geocode.search.hereapi.com/v1/geocode?q={address}&lang=en-US"
        )

        header = {"Authorization": f"Bearer {self.get_token()}"}

        response = self._send_request("GET", geocode_api_url, headers=header)

        return GeocodeCachedResponse(response.json())
