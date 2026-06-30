###############################################################################
#
# Copyright (c) 2023 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from typing import List

import flexpolyline

from .api import API


class RoutingObj:
    """
    Holds informations from one entry from RoutingAPI.routing_request() response.
    """

    def __init__(
        self,
        polyline,
        origin_point,
        dest_point,
        summary: dict,
    ):
        self.polyline = polyline
        self.origin_point = origin_point
        self.dest_point = dest_point
        self.summary = summary

    def get_polyline(self):
        return self.polyline

    def get_origin_point(self):
        return self.origin_point

    def get_dest_point(self):
        return self.dest_point

    def get_summary(self):
        return self.summary


class RoutingCachedResponse:
    def __init__(self, response: dict):
        """
        Creates cached response from RoutingAPI.routing_request().
        Holds list of RoutingObj.
        """
        self.results: List[RoutingObj] = []
        route_response = response["routes"]
        if route_response:
            for route in route_response:
                polyline_str = route["sections"][0]["polyline"]
                # polyline to list of coordinates
                polyline = flexpolyline.decode(polyline_str)
                origin_point = polyline[0]
                dest_point = polyline[len(polyline) - 1]
                summary = route["sections"][0]["summary"]
                self.results.append(
                    RoutingObj(
                        polyline=polyline,
                        origin_point=origin_point,
                        dest_point=dest_point,
                        summary=summary,
                    )
                )

    def get_routing_objects(self) -> List[RoutingObj]:
        return self.results


class RoutingAPI(API):
    def routing_request(
        self, transport_mode, origin_lat, origin_lon, dest_lat, dest_lon
    ) -> RoutingCachedResponse:
        """
        Sends a request based on inputs
        <latitude>,<longitude>

        return: cached response as RoutingCachedRsponse
        """
        routing_url = (
            f"https://router.hereapi.com/v8/routes?transportMode={transport_mode}&"
            f"origin={origin_lat},{origin_lon}&"
            f"destination={dest_lat},{dest_lon}&return=summary,polyline"
        )

        response = self._send_request("GET", routing_url)

        return RoutingCachedResponse(response.json())
