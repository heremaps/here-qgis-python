###############################################################################
#
# Copyright (c) 2023 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from typing import List, Optional, Tuple, cast

from geojson import FeatureCollection

from .api import API, APIResponseError


class IMLBoundingBox:
    def __init__(self, x_min: float, y_min: float, x_max: float, y_max: float):
        self.coordinates = (x_min, y_min, x_max, y_max)

    def get_bbox(self) -> Tuple[float, float, float, float]:
        """Returns the bounding box coordinates.
        (x_min, y_min, x_max, y_max)
        """
        return self.coordinates

    @classmethod
    def from_dict(cls, coords: dict) -> "IMLBoundingBox":
        return cls(**coords)


class IMLCachedResponse:
    def __init__(self):
        self.layer_name: Optional[str] = None
        self.features: Optional[FeatureCollection] = None

    def with_layer_name(self, name: str) -> "IMLCachedResponse":
        self.layer_name = name
        return self

    def with_features(self, features: FeatureCollection) -> "IMLCachedResponse":
        self.features = features
        return self

    def get_layer_name(self) -> Optional[str]:
        return self.layer_name

    def get_features(self) -> Optional[FeatureCollection]:
        return self.features


class IMLApiException(Exception):
    def __init__(self, catalog_hrn, layer_id, bbox):
        super().__init__(
            f"No data found for catalog_hrn - {catalog_hrn}, layer_id - {layer_id},"
            f" bbox - {bbox.get_bbox()}"
        )


class IMLMapResponse:
    def __init__(self, response):
        self.response = response

    def get_list_of_map_hrn(self) -> List[str]:
        """Returns a list of available maps for the token."""
        return [map_item["hrn"] for map_item in self.response["items"]]

    def get_layers(self, map_hrn: Optional[str] = None) -> List[str]:
        """Returns a list of available layers in the specified catalog/map."""
        layers = []
        for map_item in self.response["items"]:
            if map_hrn is None or map_item["hrn"] == map_hrn:
                layers.extend(layer["hrn"] for layer in map_item["layers"])
        return layers

    def get_total(self):
        return self.response["total"]

    def get_count(self):
        return self.response["count"]

    def get_items(self):
        return self.response["items"]


class IMLMapApi(API):
    """
    API for IML Map (experimental feature of IML API)
    """

    def fetch_maps(self) -> IMLMapResponse:
        """
        Fetches maps and returns the response .

        returns: IMLMapResponse
        """
        map_url = "https://config.data.api.platform.here.com/config/v1/maps"

        response = self._send_request("GET", map_url)
        return IMLMapResponse(response.json())

    def fetch_release_maps(self) -> list[dict]:
        """
        Fetches the list of released IML maps sorted by creation date

        returns: list[dict]
        """
        url = (
            "https://config.data.api.platform.here.com/config/v1/maps"
            f"?released={True}"
            f"&limit={100}"
            f"&sortBy={'created'}"
            f"&sortOrder={'desc'}"
        )
        data = self._send_request("GET", url)
        data = data.json()
        items = data.get("items", [])
        return items

    def get_features_by_bbox(
        self,
        catalog_hrn: str,
        layer_id: str,
        bbox: IMLBoundingBox,
        iml_context: str = "default",
        query: str = "",
    ) -> IMLCachedResponse:
        """Retrieves features based on catalog_hrn, layer_id, bbox and context

        :param str catalog_hrn: The catalog hrn which the layer should be loaded
        :param str layer_id: The layer_id which the data should be loaded
        :param IMLBoundingBox bbox: The bounding box of the request
        :param str iml_context:
            The context where the operation will be performed on a composite layer.

        :return: FeatureCollection as dict

        :raises: IMLApiException: if features is empty

        """
        bbox_coordinates = bbox.get_bbox()
        url = (
            "https://interactive.data.api.platform.here.com/interactive/v1/"
            f"catalogs/{catalog_hrn}/"
            f"layers/{layer_id}/bbox?"
            f"west={bbox_coordinates[0]}&"
            f"south={bbox_coordinates[1]}&"
            f"east={bbox_coordinates[2]}&"
            f"north={bbox_coordinates[3]}&context={iml_context}&{query}"
        )

        layer_name = self.get_layer_name(catalog_hrn, layer_id)

        response = self._send_request_with_project_scope("GET", url)
        features = cast(FeatureCollection, response.json())

        if features:
            return (
                IMLCachedResponse().with_features(features).with_layer_name(layer_name)
            )

        raise IMLApiException(catalog_hrn, layer_id, bbox)

    def get_layer_name(self, catalogHrn: str, layer_id: str) -> Optional[str]:
        """
        Fetch the catalog by HRN and return the name of the given layer ID.
        """
        url = (
            f"https://config.data.api.platform.here.com/config/v1/catalogs/{catalogHrn}"
        )

        try:
            response = self._send_request_with_project_scope("GET", url)
            data = response.json()

            # Find layer name by ID
            return next(
                (
                    layer["name"]
                    for layer in data.get("layers", [])
                    if layer.get("id") == layer_id
                ),
                None,
            )

        except Exception as e:
            raise APIResponseError(f"Error fetching layer name: {e}")
