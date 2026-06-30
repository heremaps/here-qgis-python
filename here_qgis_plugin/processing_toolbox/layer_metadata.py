# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import json
import time
from typing import Literal, TypedDict, Union

from qgis.core import QgsLayerTreeLayer, QgsLayerTreeNode, QgsMapLayer, QgsVectorLayer

from .. import __version__ as PLUGIN_VERSION


class MigratedMetadata(TypedDict):
    plugin_key: str
    plugin_version: str
    original_meta: str


LayerType = Union[
    Literal["IML"], Literal["VML"], Literal["vml_metadata"], Literal["maptile"]
]


class HereSourceMetadata(TypedDict):
    project_hrn: str
    catalog_hrn: str
    layer_type: LayerType
    layer_id: str


class LayerMetadata:
    LayerOrNode = Union[QgsVectorLayer, QgsLayerTreeNode]
    KEY_MIGRATED_FROM = "here_qgis_plugin/migrated_from"
    KEY_RELOADED = "here_qgis_plugin/reloaded"
    KEY_PLUGIN_VERSION = "here_qgis_plugin/version"
    KEY_SOURCE = "here_qgis_plugin/source"
    KEY_GROUP_LOADER = "here_qgis_plugin/group_loader"
    GROUP_LOADER_FILETYPE = "filetype"
    GROUP_LOADER_GROUP_NAME = "group_name"
    KEY_LOADER = "here_qgis_plugin/loader"
    LOADER_STYLE = "style"
    IML_CONTEXT = "context"

    # source

    @classmethod
    def set_source(
        cls,
        vlayer: LayerOrNode,
        project_hrn: str,
        catalog_hrn: str,
        layer_id: str = "",
        layer_type: LayerType = "IML",
    ):
        """

        + For IML/VML layer, all arguments must be non-empty
        + For maptile (raster layer), ``layer_id`` is maptile_id,
          ``project_hrn``, ``catalog_hrn`` can be empty
        + ``layer_id`` can be empty for group node

        :param vlayer: QgsMapLayer or QgsLayerTreeNode (group/layer)
        :param project_hrn:
        :param catalog_hrn:
        :param layer_id:
        :param layer_type: LayerType: IML, VML, maptile, etc.
        """
        cls._add_source_props(
            vlayer,
            HereSourceMetadata(
                project_hrn=project_hrn,
                catalog_hrn=catalog_hrn,
                layer_id=layer_id,
                layer_type=layer_type,
            ),
        )
        cls._set_plugin_version(vlayer)

    @classmethod
    def is_plugin_layer(cls, layer: LayerOrNode) -> bool:
        """

        :param layer: QgsMapLayer or QgsLayerTreeNode (group/layer)
        :return: True if the layer or node was created by the plugin
         (by calling ``set_source()``)
        """
        return bool(cls._get_source_props(layer))

    @classmethod
    def get_project_hrn(cls, vlayer: LayerOrNode):
        return cls._get_source_props(vlayer).get("project_hrn")

    @classmethod
    def get_catalog_hrn(cls, vlayer: LayerOrNode):
        return cls._get_source_props(vlayer).get("catalog_hrn")

    @classmethod
    def get_layer_id(cls, vlayer: LayerOrNode):
        return cls._get_source_props(vlayer).get("layer_id")

    @classmethod
    def get_layer_type(cls, vlayer: LayerOrNode):
        return cls._get_source_props(vlayer).get("layer_type")

    @classmethod
    def set_layer_id(cls, vlayer: LayerOrNode, layer_id: str):
        cls._add_source_props(vlayer, dict(layer_id=layer_id))

    @classmethod
    def get_plugin_version(cls, layer: LayerOrNode):
        return layer.customProperty(LayerMetadata.KEY_PLUGIN_VERSION)

    @classmethod
    def _set_plugin_version(cls, layer: LayerOrNode):
        cls._set_property(layer, LayerMetadata.KEY_PLUGIN_VERSION, PLUGIN_VERSION)

    # utils

    @classmethod
    def _set_property(cls, vlayer: LayerOrNode, key: str, value: str):
        vlayer.setCustomProperty(key, value)

    @classmethod
    def get_json_props(cls, vlayer: LayerOrNode, key: str) -> dict:
        # QgsVectorLayer.customProperties() -> dict
        # QgsLayerTreeNode.customProperties() -> list
        return json.loads(vlayer.customProperty(key, "{}"))

    @classmethod
    def _get_json_property(cls, vlayer: LayerOrNode, key: str, prop: str):
        json_props = cls.get_json_props(vlayer, key)
        return json_props.get(prop)

    @classmethod
    def _add_json_props(cls, vlayer: LayerOrNode, key: str, **props):
        json_props = cls.get_json_props(vlayer, key)
        json_props.update(props)
        cls._set_property(vlayer, key, json.dumps(json_props))

    @classmethod
    def _remove_json_props(cls, vlayer: LayerOrNode, key: str, *props):
        json_props = cls.get_json_props(vlayer, key)
        for prop in props:
            json_props.pop(prop, "")
        cls._set_property(vlayer, key, json.dumps(json_props))

    @classmethod
    def _add_source_props(cls, vlayer_or_qnode: LayerOrNode, props: HereSourceMetadata):
        return cls._add_json_props(vlayer_or_qnode, LayerMetadata.KEY_SOURCE, **props)

    @classmethod
    def _get_source_props(cls, vlayer: LayerOrNode) -> HereSourceMetadata:
        return cls.get_json_props(vlayer, LayerMetadata.KEY_SOURCE)

    @classmethod
    def _add_group_loader_props(cls, vlayer_or_qnode: LayerOrNode, **props):
        return cls._add_json_props(
            vlayer_or_qnode, LayerMetadata.KEY_GROUP_LOADER, **props
        )

    @classmethod
    def _get_group_loader_property(cls, vlayer: LayerOrNode, prop: str):
        return cls._get_json_property(vlayer, LayerMetadata.KEY_GROUP_LOADER, prop)

    @classmethod
    def add_loader_props(cls, vlayer_or_qnode: LayerOrNode, **props):
        return cls._add_json_props(vlayer_or_qnode, LayerMetadata.KEY_LOADER, **props)

    @classmethod
    def get_loader_property(cls, vlayer: LayerOrNode, prop: str):
        return cls._get_json_property(vlayer, LayerMetadata.KEY_LOADER, prop)

    # loader

    @classmethod
    def get_layer_id_from_style(cls, vlayer: LayerOrNode):
        prop = cls.get_loader_property(vlayer, cls.LOADER_STYLE)
        if not prop:
            return None
        return json.loads(prop).get("layer_id")

    @classmethod
    def set_style(cls, vlayer: LayerOrNode, style_set_str):
        cls.add_loader_props(vlayer, style=style_set_str)

    @classmethod
    def get_style(cls, vlayer: LayerOrNode):
        return cls.get_loader_property(vlayer, cls.LOADER_STYLE)

    @classmethod
    def set_iml_context(cls, vlayer: LayerOrNode, context):
        cls.add_loader_props(vlayer, iml_context=context)

    @classmethod
    def get_iml_context(cls, vlayer: LayerOrNode):
        context = cls.get_loader_property(vlayer, cls.IML_CONTEXT)
        if not context:
            return "default"
        return context

    @classmethod
    def set_filetype(cls, vlayer: LayerOrNode, filetype):
        cls._add_group_loader_props(vlayer, **{cls.GROUP_LOADER_FILETYPE: filetype})

    @classmethod
    def get_filetype(cls, vlayer: LayerOrNode):
        return cls._get_group_loader_property(vlayer, cls.GROUP_LOADER_FILETYPE)

    @classmethod
    def set_group_name(cls, vlayer: LayerOrNode, group_name):
        cls._add_group_loader_props(vlayer, **{cls.GROUP_LOADER_GROUP_NAME: group_name})

    @classmethod
    def get_group_name(cls, vlayer: LayerOrNode):
        return cls._get_group_loader_property(vlayer, cls.GROUP_LOADER_GROUP_NAME)

    @classmethod
    def set_migrated_metadata(
        cls, vlayer_or_qnode: LayerOrNode, metadata: MigratedMetadata
    ):
        return cls._add_json_props(
            vlayer_or_qnode, LayerMetadata.KEY_MIGRATED_FROM, **metadata
        )

    # other

    @classmethod
    def get_migrated_metadata(cls, vlayer: LayerOrNode) -> MigratedMetadata:
        metadata: MigratedMetadata = cls.get_json_props(
            vlayer, LayerMetadata.KEY_MIGRATED_FROM
        )
        return metadata

    @staticmethod
    def set_reloaded(vlayer: QgsVectorLayer):
        vlayer.setCustomProperty(
            LayerMetadata.KEY_RELOADED, "{:.0f}".format(time.time())
        )

    @staticmethod
    def get_reloaded(vlayer: QgsVectorLayer):
        return vlayer.customProperty(LayerMetadata.KEY_RELOADED, "")

    # copy
    @classmethod
    def copy_metadata(cls, layer_from: LayerOrNode, layer_to: LayerOrNode) -> bool:
        # TODO
        keys = [
            cls.KEY_SOURCE,
            cls.KEY_GROUP_LOADER,
            cls.KEY_RELOADED,
            cls.KEY_PLUGIN_VERSION,
        ]
        is_layer = False
        if isinstance(layer_to, (QgsLayerTreeLayer,)):
            # only copy style from QgsMapLayer to QgsLayerTreeLayer
            is_layer = True
            keys.extend([cls.KEY_LOADER])
        elif isinstance(layer_to, (QgsMapLayer,)):
            is_layer = True
        for key in keys:
            value = layer_from.customProperty(key)
            if value is not None:
                cls._set_property(layer_to, key, value)
        if not is_layer:
            cls._remove_json_props(layer_to, cls.KEY_SOURCE, "layer_id")
        return True


class LayerMetadataPluginV1:
    KEY_META = "XYZHub/meta"
    KEY_CONN = "XYZHub/conn"
    KEY_LOADER = "XYZHub/loader"
    KEY_VERSION = "XYZHub/version"

    @classmethod
    def detect_feature_type(cls, vlayer: QgsVectorLayer):
        prop = vlayer.customProperty(cls.KEY_META)
        if not prop:
            return None
        return json.loads(prop).get("id")

    @classmethod
    def is_V1_layer(cls, vlayer: QgsVectorLayer):
        return bool(vlayer.customProperty(cls.KEY_META, ""))

    @classmethod
    def make_compatible_v2(cls, vlayer: QgsVectorLayer):
        old_metadata = json.loads(vlayer.customProperty(cls.KEY_META))
        catalog_hrn = old_metadata["catalog_hrn"]
        project_hrn = (
            ""
            if "project_item" not in old_metadata.keys()
            else old_metadata["project_item"]["hrn"]
        )
        old_plugin_version = vlayer.customProperty(cls.KEY_VERSION)
        LayerMetadata.set_source(vlayer, project_hrn, catalog_hrn)
        LayerMetadata.set_migrated_metadata(
            vlayer,
            MigratedMetadata(
                plugin_key=cls.KEY_META,
                plugin_version=old_plugin_version,
                original_meta=old_metadata,
            ),
        )


class BackwardCompatibilityMetadata:
    @staticmethod
    def make_compatible(vlayer: QgsVectorLayer):
        loader_str = json.dumps(
            {
                "limit": 100,
                "max_feat": 1000000,
                "similarity_treshold": 0,
                "similarity_mode": "single",
                "loading_mode": "incremental",
                "tile_schema": "web",
            }
        )
        catalog_hrn = LayerMetadata.get_catalog_hrn(vlayer)
        layer_id = LayerMetadata.get_layer_id(vlayer)
        conn_str = json.dumps(
            {
                "token": "",
                "server": "PLATFORM_PRD",
                "here_credentials": "",
                "user_login": "email",
                "realm": "",
                # "catalog":
                "catalog_hrn": catalog_hrn,
                "hrn": catalog_hrn + ":" + layer_id,
            }
        )
        meta_str = json.dumps({})
        vlayer.setCustomProperty(LayerMetadataPluginV1.KEY_LOADER, loader_str)
        vlayer.setCustomProperty(LayerMetadataPluginV1.KEY_CONN, conn_str)
        vlayer.setCustomProperty(LayerMetadataPluginV1.KEY_META, meta_str)
