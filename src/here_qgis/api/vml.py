# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from geojson import Feature, FeatureCollection

# TODO: find replacement
from here.geotiles import heretile

from .api import API


def geometry_from_partition_id(partition_id: str):
    return heretile.get_polygon(partition_id)


def is_valid_partition_id(partition_id: str):
    return heretile.is_valid(partition_id)


class VMLBoundingBox:
    def __init__(self, x_min, y_min, x_max, y_max, level):
        self.x_min, self.y_min, self.x_max, self.y_max, self.level = (
            x_min,
            y_min,
            x_max,
            y_max,
            level,
        )

    def get_bbox(self, level: int = None):
        return dict(
            west=self.x_min,
            south=self.y_min,
            east=self.x_max,
            north=self.y_max,
            level=level or self.level,
        )

    @classmethod
    def from_dict(cls, coords: dict):
        return cls(**coords)


class VMLApi(API):
    def _send_vml_request(self, method, url) -> dict:
        resp = self._send_request_with_project_scope(method, url)
        return resp.json()

    def get_partitions_metadata(
        self,
        catalog_hrn: str,
        layer_id: str,
        partition_ids: list,
        version: int,
    ):
        url = (
            "https://sab.query.data.api.platform.here.com/query/v1/catalogs"
            f"/{catalog_hrn}/layers/{layer_id}/partitions?"
        )
        sep = "&"
        queries = [
            "&".join(f"partition={partition_id}" for partition_id in partition_ids),
            f"version={version}",
            "additionalFields=dataSize,compressedDataSize",
        ]
        url += sep.join(queries)
        return self._send_vml_request("GET", url)

    def get_partitions_data_handles(
        self,
        catalog_hrn: str,
        layer_id: str,
        partition_ids: list,
        version: int,
    ):
        metadata = self.get_partitions_metadata(
            catalog_hrn, layer_id, partition_ids, version
        )

        data_handles = []
        for partition in metadata["partitions"]:
            data_handles.append(partition["dataHandle"])
        return data_handles

    def get_partition_data(
        self,
        catalog_hrn: str,
        layer_id: str,
        data_handle: str,
    ):
        url = (
            "https://sab.blob.data.api.platform.here.com/blobstore/v1/catalogs"
            f"/{catalog_hrn}/layers/{layer_id}/data/{data_handle}"
        )

        return self._send_vml_request("GET", url)

    def get_features_by_partition_ids(
        self,
        catalog_hrn: str,
        layer_id: str,
        tile_ids: list,
        version: int = None,
    ):
        data = []
        if not version:
            version = self.get_latest_version(catalog_hrn)
        data_handles = self.get_partitions_data_handles(
            catalog_hrn,
            layer_id,
            tile_ids,
            version,
        )
        metadatas = self.get_partitions_metadata(
            catalog_hrn,
            layer_id,
            tile_ids,
            version,
        )
        for idx, tile_id in enumerate(tile_ids):
            feature_coll = self.get_partition_data(
                catalog_hrn, layer_id, data_handles[idx]
            )
            data.append(
                (
                    {
                        "id": tile_id,
                        "version": version,
                        "data_handle": data_handles[idx],
                        "data_size": metadatas["partitions"][idx]["dataSize"],
                    },
                    feature_coll,
                )
            )
        return data

    def get_latest_version(self, catalog_hrn: str):
        url = (
            "https://sab.metadata.data.api.platform.here.com/metadata/v1/catalogs"
            f"/{catalog_hrn}/versions/latest?startVersion=1"
        )
        resp = self._send_vml_request("GET", url)
        return resp["version"]

    def get_level(self, catalog_hrn: str, layer_id: str):
        url = (
            "https://config.data.api.platform.here.com/config/v1/catalogs/"
            f"{catalog_hrn}"
        )
        resp = self._send_vml_request("GET", url)
        layer_details = {}
        for resp_layer in resp["layers"]:
            if resp_layer["id"] == layer_id:
                layer_details = resp_layer
                break
        partitioning_details = layer_details.get("partitioning")
        level = None
        if partitioning_details and partitioning_details["scheme"] == "heretile":
            level = partitioning_details["tileLevels"][-1]
        return level

    def partition_ids_from_bbox_with_level(self, bbox, catalog_hrn, layer_id):
        level = self.get_level(catalog_hrn, layer_id)
        partition_ids = list(
            heretile.in_bounding_box(fully_contained=False, **bbox.get_bbox(level))
        )
        return partition_ids

    def get_features_by_bbox(
        self,
        catalog_hrn: str,
        layer_id: str,
        bbox: VMLBoundingBox,
        version: int = None,
        limit: int = None,
    ):
        """
        Retrieves features from specified catalog_hrn, layer_id by bounding box

        return: FeatureCollection as a dict
        """

        partition_ids = self.partition_ids_from_bbox_with_level(
            bbox, catalog_hrn, layer_id
        )
        if limit:
            partition_ids = partition_ids[:limit]

        return self.get_features_by_partition_ids(
            catalog_hrn, layer_id, partition_ids, version
        )

    def get_partitions_by_bbox_as_geojson(
        self,
        catalog_hrn: str,
        layer_id: str,
        bbox: VMLBoundingBox,
        limit: int = None,
        version: int = None,
    ) -> FeatureCollection:
        partition_ids = self.partition_ids_from_bbox_with_level(
            bbox, catalog_hrn, layer_id
        )

        if limit:
            partition_ids = partition_ids[:limit]
        if not version:
            version = self.get_latest_version(catalog_hrn)
        metadata = self.get_partitions_metadata(
            catalog_hrn, layer_id, partition_ids, version
        )
        return FeatureCollection(
            list(
                Feature(
                    id=partition["partition"],
                    geometry=geometry_from_partition_id(partition["partition"]),
                    properties=dict(
                        id=partition["partition"],
                        data_handle=partition["dataHandle"],
                        data_size=partition["dataSize"],
                        compressed_data_size=partition["compressedDataSize"],
                        version=partition["version"],
                        # billing_tag=partition.billing_tag,
                    ),
                )
                for partition in metadata["partitions"]
            )
        )
