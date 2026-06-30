###############################################################################
#
# Copyright (c) 2023 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import json
import os
from typing import TypedDict, Union


class StyleSetInfo(TypedDict):
    layer_id: str
    style_set_name: str
    geom_type: str


class StyleSetNotFound(Exception):
    def __init__(self, msg):
        super().__init__(msg)


class StyleConfig:
    MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
    STYLE_DIR = os.path.join(MODULE_DIR, "style_set_24_01_30")
    STYLE_LAYER_IDS = [
        "address",
        "admin",
        "building",
        "cartoLine",
        "cartoPolygon",
        "lane",
        "place",
        "relation",
        "sign",
        "topology",
        "density",
    ]
    LAYER_IDS = [
        "address",
        "admin",
        "building",
        "carto",
        "lane",
        "place",
        "relation",
        "sign",
        "topology",
        "density",
    ]

    NO_STYLE_QML = ""

    OSM_POLYGON_STYLE_LAYER_IDS = ["building", "cartoPolygon"]
    STYLE_MAP = {
        "No style": NO_STYLE_QML,
        "Standard": {
            layer_id: os.path.join("Standard", f"{layer_id}.qml")
            for layer_id in STYLE_LAYER_IDS
        },
        "Standard Color compare (blue)": {
            layer_id: os.path.join("Standard Color compare", "blue", f"{layer_id}.qml")
            for layer_id in STYLE_LAYER_IDS
        },
        "Standard Color compare (red)": {
            layer_id: os.path.join("Standard Color compare", "red", f"{layer_id}.qml")
            for layer_id in STYLE_LAYER_IDS
        },
        "OSM version compare color (red)": {
            layer_id: os.path.join(
                "OSM version compare color", "polygon_version_label_red.qml"
            )
            for layer_id in OSM_POLYGON_STYLE_LAYER_IDS
        },
        "OSM version compare color (blue)": {
            layer_id: os.path.join(
                "OSM version compare color", "polygon_version_label_blue.qml"
            )
            for layer_id in OSM_POLYGON_STYLE_LAYER_IDS
        },
        "OSM version compare hatched (45)": {
            layer_id: os.path.join(
                "OSM version compare hatched",
                "45_degree",
                "polygon_version_label_45_degree.qml",
            )
            for layer_id in OSM_POLYGON_STYLE_LAYER_IDS
        },
        "OSM version compare hatched (135)": {
            layer_id: os.path.join(
                "OSM version compare hatched",
                "135_degree",
                "polygon_version_label_135_degree.qml",
            )
            for layer_id in OSM_POLYGON_STYLE_LAYER_IDS
        },
        "Violation": {
            layer_id: os.path.join("Violation", "point.qml")
            for layer_id in STYLE_LAYER_IDS
        },
    }
    STYLE_GROUPS = list(STYLE_MAP.keys())
    DEFAULT_STYLE_IDX = 1
    NO_STYLE_IDX = 0

    @classmethod
    def to_info(
        cls, layer_id, style_set_idx_or_name: Union[int, str], geom_type=""
    ) -> StyleSetInfo:
        """

        :param layer_id: feature type string
        :param style_set_idx_or_name: enum index or style set name
        :param geom_type: geometry type: Point, Line, Polygon
        :return: StyleSetInfo object, used for layer styling
        """
        style_set_name = (
            cls.STYLE_GROUPS[style_set_idx_or_name]
            if isinstance(style_set_idx_or_name, int)
            else style_set_idx_or_name.strip()
        )
        return StyleSetInfo(
            layer_id=layer_id,
            style_set_name=style_set_name,
            geom_type=geom_type,
        )

    @staticmethod
    def style_set_to_str(style_set: StyleSetInfo) -> str:
        return json.dumps(style_set)

    @classmethod
    def qml_path_from_info(cls, info: StyleSetInfo) -> str:
        return cls.qml_path_from_name(
            info.get("layer_id", ""),
            info.get("style_set_name", ""),
            info.get("geom_type", ""),
        )

    @classmethod
    def qml_path(cls, layer_id, style_set_idx, geom_type=""):
        """

        :param layer_id: feature type string
        :param style_set_idx: style set index, key index in
        :py:const:`StyleConfig.STYLE_MAP`
        :param geom_type: geometry type: Point, Line, Polygon
        :return: absolute path to qml style set file
        """
        style_set_name = cls.STYLE_GROUPS[style_set_idx]
        return cls.qml_path_from_name(layer_id, style_set_name, geom_type)

    @classmethod
    def qml_path_from_name(cls, layer_id, style_set_name, geom_type=""):
        """

        :param layer_id: feature type string
        :param style_set_name: style set name, key value in
        :py:const:`StyleConfig.STYLE_MAP`
        :param geom_type: geometry type: Point, Line, Polygon
        :return: absolute path to qml style set file
        """
        style_layer_id = cls._get_style_layer_id(layer_id)
        style_by_layer = cls.STYLE_MAP.get(style_set_name)
        if style_by_layer == cls.NO_STYLE_QML:
            return cls.NO_STYLE_QML
        filename = style_by_layer.get(
            f"{style_layer_id}{geom_type.title()}",
            style_by_layer.get(style_layer_id),
        )
        qml_path = os.path.join(cls.STYLE_DIR, filename) if filename else None
        if qml_path is None or not os.path.exists(qml_path):
            raise StyleSetNotFound(
                f"qml file not found for style set '{style_set_name}' layer"
                f" '{layer_id}', alias '{style_layer_id}', geometry type '{geom_type}'"
            )
        return qml_path

    @classmethod
    def _get_style_layer_id(cls, layer_id):
        """
        Return style_layer_id (corresponds to qml style set file)
        from given layer_id (feature type string).
        In most case style_layer_id is the same as layer_id

        :param layer_id: enum value in :py:const:`StyleConfig.LAYER_IDS`
        :return: style_layer_id
        """
        style_layer_id = layer_id
        for i in cls.STYLE_LAYER_IDS:
            if i in layer_id:
                style_layer_id = i
                break
        return style_layer_id

    @classmethod
    def get_layer_id(cls, layer_idx: int):
        """
        Return layer id (feature type string). Return None if layer_idx is not valid

        :param layer_idx: enum index in :py:const:`StyleConfig.LAYER_IDS`
        :return: layer_id (feature type string)
        """
        if layer_idx is None or layer_idx < 0 or layer_idx >= len(cls.LAYER_IDS):
            return None
        return cls.LAYER_IDS[layer_idx]

    @classmethod
    def is_valid_style(cls, style_set_info: StyleSetInfo):
        is_valid = False
        try:
            qml_path = cls.qml_path_from_name(
                style_set_info["layer_id"],
                style_set_info["style_set_name"],
                style_set_info["geom_type"],
            )
            if qml_path:
                is_valid = True
        except StyleSetNotFound:
            pass
        return is_valid
