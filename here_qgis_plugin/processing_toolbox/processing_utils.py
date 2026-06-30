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
import logging
import os
from typing import List, Union, cast

from qgis.core import (
    Qgis,
    QgsEditorWidgetSetup,
    QgsFeatureRequest,
    QgsField,
    QgsGroupLayer,
    QgsLayerTree,
    QgsLayerTreeGroup,
    QgsLayerTreeLayer,
    QgsLayerTreeNode,
    QgsMapLayer,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingLayerPostProcessorInterface,
    QgsProject,
    QgsRectangle,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtCore import QMetaType, QVariant
from qgis.utils import iface

from here_qgis.helper_functions import is_json_string

from ..style_set import StyleConfig, StyleSetInfo, StyleSetNotFound
from ..utils.files import make_unique_string
from .file_type import FileType
from .layer_metadata import LayerMetadata

logger = logging.getLogger(__name__)

IML_CONTEXT = [
    ("Default (for non-composite layers)", ["default"]),
    ("Base + Branch (single layer)", ["default"]),
    ("Base", ["super"]),
    ("Branch", ["extension"]),
    ("Base + Branch (separate layers)", ["super", "extension"]),
]


def get_geom_type_str(layer: QgsVectorLayer) -> str:
    return QgsWkbTypes.geometryDisplayString(layer.geometryType())


def bbox_from_extent(extent: QgsRectangle):
    return {
        "x_min": max(-180.0, extent.xMinimum()),
        "y_min": max(-90.0, extent.yMinimum()),
        "x_max": min(180.0, extent.xMaximum()),
        "y_max": min(90.0, extent.yMaximum()),
    }


def ctlg_hrn_parser(catalog_hrn: str):
    """
    Parses folder and group name from catalog_hrn

    """
    split_hrn = catalog_hrn.split(":")
    folder_name = split_hrn[-2] + "_" + split_hrn[-1]
    group_name = split_hrn[-2] + ":" + split_hrn[-1]

    return folder_name, group_name


def isQVariant(attr):
    """
    Checks if element is QVariant NULL value. Prevents from writing to json
    """
    if isinstance(attr, QVariant) and str(attr.value()) == "NULL":
        return True
    return False


# https://github.com/qgis/QGIS/blob/f3e9aaf79a9282b28a605abd0dadaab9951050c8/python/plugins/processing/algs/qgis/ui/FieldsMappingPanel.py
# https://api.qgis.org/api/3.36/qgsvariantutils_8cpp_source.html#l00501
VALID_FIELD_TYPE = dict(
    [
        (QMetaType.Type.QDate, QVariant.Date),
        (QMetaType.Type.QDateTime, QVariant.DateTime),
        (QMetaType.Type.Double, QVariant.Double),
        (QMetaType.Type.Int, QVariant.Int),
        (QMetaType.Type.LongLong, QVariant.LongLong),
        (QMetaType.Type.QString, QVariant.String),
        (QMetaType.Type.Bool, QVariant.Bool),
    ]
)


# INFO: changed manually
def new_field(name, field_type: Union[QMetaType, QVariant]):
    try:
        field = QgsField(name, field_type)
    except TypeError:
        # TypeError is raised for QMetaType on old Qt
        # fallback to use QVariant instead
        field = QgsField(name, VALID_FIELD_TYPE.get(field_type, QVariant.String))
    return field


def get_one_feature_without_geom(vlayer, sort_by_field_name: str = ""):
    request = (
        QgsFeatureRequest().setFlags(QgsFeatureRequest.Flag.NoGeometry).setLimit(1)
    )
    if sort_by_field_name:
        request = request.addOrderBy(
            '"{}"'.format(sort_by_field_name), ascending=True, nullsfirst=False
        )
    lst = list(vlayer.getFeatures(request))
    return lst[0] if len(lst) else None


def wkb_type_to_geom_type(wkb_type_str):
    return QgsWkbTypes.geometryDisplayString(
        QgsWkbTypes.geometryType(getattr(Qgis.WkbType, wkb_type_str))
    )


class ExamplePostProcessor(QgsProcessingLayerPostProcessorInterface):
    def postProcessLayer(
        self,
        vlayer: QgsVectorLayer,
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ):
        LayerPostProcessor.update_style(vlayer)


class LayerPostProcessor:
    @staticmethod
    def detect_feature_type(vlayer: QgsVectorLayer):
        return LayerMetadata.get_layer_id(
            vlayer
        ) or LayerMetadata.get_layer_id_from_style(vlayer)

    @staticmethod
    def set_style(style_set_str: str, vlayer: QgsVectorLayer):
        LayerMetadata.set_style(vlayer, style_set_str)

    @staticmethod
    def get_style(vlayer: QgsVectorLayer):
        style_set_str = LayerMetadata.get_style(vlayer)
        if not style_set_str:
            raise StyleSetNotFound(f"Layer {vlayer} does not have style metadata")
        return StyleSetInfo(json.loads(style_set_str))

    @staticmethod
    def set_iml_context(iml_context: str, vlayer: QgsVectorLayer):
        LayerMetadata.set_iml_context(vlayer, iml_context)

    @staticmethod
    def get_iml_context(vlayer: QgsVectorLayer):
        return LayerMetadata.get_iml_context(vlayer)

    @staticmethod
    def set_filetype(filetype: str, vlayer: QgsVectorLayer):
        LayerMetadata.set_filetype(vlayer, filetype)

    @staticmethod
    def set_group_name(group_name: str, vlayer: QgsVectorLayer):
        LayerMetadata.set_group_name(vlayer, group_name)

    @staticmethod
    def get_group_name(vlayer):
        return LayerMetadata.get_group_name(vlayer)

    @staticmethod
    def update_style(vlayer: QgsVectorLayer) -> bool:
        # TODO: raise Exception, client needs to handle it
        style_set_str = LayerMetadata.get_style(vlayer)
        if not style_set_str:
            return False
        try:
            style_set_info = json.loads(style_set_str)
            style_qml_path = StyleConfig.qml_path_from_info(style_set_info)
        except Exception as e:
            logger.error("update_style failed for layer '%s': %s", vlayer, e)
            style_qml_path = ""
        if style_qml_path:
            msg, status = vlayer.loadNamedStyle(style_qml_path)
            return status
        return False

    @staticmethod
    def update_layer(vlayer):
        # do not update/edit layer to prevent bugs
        return

        # TODO: find other way to set QgsField to String (instead JSON) for styling
        filetype = LayerMetadata.get_filetype(vlayer)
        if filetype == FileType.GEOJSON.name:
            # Get the existing fields
            existing_fields = vlayer.fields()
            # Create a list of new fields with String data type
            new_fields = [
                new_field(field.name(), QVariant.String) for field in existing_fields
            ]
            vlayer.dataProvider().enterUpdateMode()
            # Remove all existing fields from the iml
            vlayer.dataProvider().deleteAttributes(list(range(len(existing_fields))))
            # Add the new string fields to the iml
            vlayer.dataProvider().addAttributes(new_fields)
            # Update the fields to make sure changes are applied
            vlayer.updateFields()
            vlayer.dataProvider().leaveUpdateMode()

    @staticmethod
    def add_layer_into_context(context: QgsProcessingContext, layer: QgsMapLayer):
        layer_name = layer.name()
        # save layer to context
        details = QgsProcessingContext.LayerDetails(
            layer_name, context.project(), layer_name
        )
        details.forceName = True
        context.addLayerToLoadOnCompletion(
            layer.id(),
            details,
        )
        context.temporaryLayerStore().addMapLayer(layer)

    @staticmethod
    def get_layers_from_context(context: QgsProcessingContext):
        for vlayer_id, _details in context.layersToLoadOnCompletion().items():
            vlayer = context.temporaryLayerStore().mapLayer(vlayer_id)
            if not vlayer:
                logger.warning(
                    "Qgis layer not found from QgsProcessingContext for id: %s",
                    vlayer_id,
                )
            else:
                yield vlayer

    @staticmethod
    def zoom_to_layer_selection(vlayer):
        # zoom to selected
        vlayer.selectAll()
        canvas = iface and iface.mapCanvas() or QgsMapCanvas()
        canvas.zoomToSelected()
        vlayer.removeSelection()

    @staticmethod
    def zoom_to_layer(vlayer):
        # zoom to layer
        # https://github.com/qgis/QGIS/blob/release-3_30/src/gui/layertree/qgslayertreeviewdefaultactions.cpp#L370
        canvas = iface and iface.mapCanvas() or QgsMapCanvas()
        extent = vlayer.extent()
        extent = canvas.mapSettings().layerExtentToOutputExtent(vlayer, extent)
        canvas = iface and iface.mapCanvas() or QgsMapCanvas()
        extent.scale(1.05)
        canvas.setExtent(extent, True)
        canvas.refresh()

    @classmethod
    def enable_json_view(cls, vlayer):
        feat = get_one_feature_without_geom(vlayer)
        if not feat:
            return

        View_Text = 0
        FormatJson_Indented = 0
        formType = "JsonEdit"
        formConfig = {"DefaultView": View_Text, "FormatJson": FormatJson_Indented}
        for i, field in enumerate(vlayer.fields()):
            if cls.is_json_field(vlayer, field):
                vlayer.setEditorWidgetSetup(
                    i, QgsEditorWidgetSetup(formType, formConfig)
                )

    @staticmethod
    def is_json_field(vlayer, field):
        field_type = field.typeName()
        if field_type == "JSON":
            return True
        elif field_type == "String":
            field_name = field.name()
            feat = get_one_feature_without_geom(vlayer, sort_by_field_name=field_name)
            if is_json_string(feat.attribute(field_name)):
                return True
        return False

    @classmethod
    def post_process(
        cls, context: QgsProcessingContext, feedback: QgsProcessingFeedback
    ) -> List[str]:
        vlayer_ids = []
        for vlayer in cls.get_layers_from_context(context):
            LayerPostProcessor.update_layer(vlayer)
            LayerPostProcessor.update_style(vlayer)
            LayerPostProcessor.enable_json_view(vlayer)
            vlayer_ids.append(vlayer.id())
        return vlayer_ids

    @classmethod
    def get_group_name_from_context(cls, context: QgsProcessingContext):
        for vlayer in cls.get_layers_from_context(context):
            group_name = cls.get_group_name(vlayer)
            if group_name:
                return group_name

    @classmethod
    def group_layers(cls, context: QgsProcessingContext):
        root = context.project().layerTreeRoot()
        group_name = cls.get_group_name_from_context(context)
        group = root.findGroup(group_name)
        if not group:
            group = root.addGroup(group_name)
        for vlayer in cls.get_layers_from_context(context):
            owned_map_layer = context.temporaryLayerStore().takeMapLayer(vlayer)
            if owned_map_layer:
                context.project().addMapLayer(owned_map_layer, False)
                group.addLayer(owned_map_layer)

    @staticmethod
    def mark_dangling_layer(vlayer: QgsVectorLayer, dangling_file_uri: str):
        layers = LayerMetadata.get_loader_property(vlayer, "dangling_layer") or dict()
        base_file_uri = dangling_file_uri.split("|")[0]
        layers.update({base_file_uri: 1})
        LayerMetadata.add_loader_props(vlayer, dangling_layer=layers)

    @staticmethod
    def remove_dangling_layers(vlayer: QgsVectorLayer):
        layers = LayerMetadata.get_loader_property(vlayer, "dangling_layer") or dict()
        for layer_uri in layers:
            try:
                os.remove(layer_uri)
            except Exception as e:
                logger.error("Failed to remove dangling layer: %s", e)

    @classmethod
    def remove_dangling_layers_from_context(cls, context: QgsProcessingContext):
        for vlayer in cls.get_layers_from_context(context):
            cls.remove_dangling_layers(vlayer)


class LayerGroupPostProcessor:
    @classmethod
    def sort_group(cls, group: QgsLayerTreeGroup):
        group.setExpanded(True)
        sorted_vlayer = sorted(
            [layer.layer() for layer in group.findLayers()],
            key=LayerSorter().sorting_key,
        )
        sorted_vlayer = list(
            map(
                lambda layer: (layer, group.findLayer(layer.id()).isVisible()),
                sorted_vlayer,
            )
        )

        # save current children for remove
        children = group.children()

        # layer ordering according to handleAlgorithmResults
        # https://github.com/qgis/QGIS/blob/master/python/plugins/processing/gui/Postprocessing.py
        for vlayer, is_visible in sorted_vlayer:
            child = QgsLayerTreeLayer(vlayer)
            LayerMetadata.copy_metadata(vlayer, child)
            child.setExpanded(False)
            child.setItemVisibilityChecked(is_visible)
            group.addChildNode(child)

        for child in children:
            group.takeChild(child)
        return group

    @classmethod
    def create_layer_group(cls, group_name: str, context: QgsProcessingContext):
        # group = root.findGroup(group_name) or root.insertGroup(0, group_name)
        group = QgsLayerTreeGroup(make_unique_string("{} {}", group_name))
        group.setExpanded(True)
        sorted_vlayer = sorted(
            (
                context.temporaryLayerStore().mapLayer(vlayer_id)
                for vlayer_id in context.layersToLoadOnCompletion()
            ),
            key=LayerSorter().sorting_key,
        )
        context.setLayersToLoadOnCompletion(dict())
        # layer ordering according to handleAlgorithmResults
        # https://github.com/qgis/QGIS/blob/master/python/plugins/processing/gui/Postprocessing.py
        sorted_layer_node = list()
        for vlayer in sorted_vlayer:
            own_vlayer = context.temporaryLayerStore().takeMapLayer(vlayer)
            if own_vlayer:
                context.project().addMapLayer(own_vlayer, False)
                child = QgsLayerTreeLayer(own_vlayer)
            else:
                child = QgsLayerTreeLayer(vlayer)
            sorted_layer_node.append(child)
            LayerMetadata.copy_metadata(vlayer, child)
            LayerMetadata.copy_metadata(vlayer, group)

        for child in sorted_layer_node:
            child.setExpanded(False)
            group.addChildNode(child)
        return group

    @staticmethod
    def insert_group_to_root(context: QgsProcessingContext, group: QgsLayerTreeGroup):
        if not len(group.children()):
            return False
        root = context.project().layerTreeRoot()
        # group of layers
        root.insertChildNode(0, group)
        return True

    @staticmethod
    def create_glayer(group_name: str, context: QgsProcessingContext):
        sorted_vlayer = sorted(
            (
                context.temporaryLayerStore().mapLayer(vlayer_id)
                for vlayer_id in context.layersToLoadOnCompletion()
            ),
            key=LayerSorter().sorting_key,
        )
        context.setLayersToLoadOnCompletion(dict())
        # layer ordering according to handleAlgorithmResults
        # https://github.com/qgis/QGIS/blob/master/python/plugins/processing/gui/Postprocessing.py
        for vlayer in sorted_vlayer:
            context.temporaryLayerStore().takeMapLayer(vlayer)

        # group layer
        glayer = QgsGroupLayer(
            group_name, QgsGroupLayer.LayerOptions(context.transformContext())
        )
        glayer.setChildLayers(reversed(sorted_vlayer))
        context.project().addMapLayer(glayer, False)
        return glayer

    @staticmethod
    def insert_glayer_to_root(context: QgsProcessingContext, glayer: QgsGroupLayer):
        root = context.project().layerTreeRoot()
        # group layer
        root.insertLayer(0, glayer)
        return True

    @staticmethod
    def sort_groups(group: QgsLayerTreeGroup = None):
        group = group or QgsProject.instance().layerTreeRoot()
        sorter = QNodeSorter(group.children())

        lst_qnode = list(sorted(group.children(), key=sorter.sorting_key))
        print("sort_groups", lst_qnode)
        for qnode in lst_qnode:
            group.takeChild(qnode)
            group.addChildNode(qnode)


class QNodeSorter:
    def __init__(self, children: List[QgsLayerTreeNode]):
        self.initial_order = {qnode.dump(): i for i, qnode in enumerate(children)}
        self.project_order = {
            LayerMetadata.get_project_hrn(qnode): i for i, qnode in enumerate(children)
        }
        self.cache = dict()

    def sorting_key(self, qnode: QgsLayerTreeNode):
        qnode_key = qnode.dump()
        order_point = self.cache.get(qnode_key)
        if order_point is None:
            initial_order = self.initial_order.get(qnode_key, 0)
            project_order = self.project_order.get(
                LayerMetadata.get_project_hrn(qnode), 0
            )
            is_layer = QgsLayerTree.isLayer(qnode)
            is_group = not is_layer
            mapmaking_order = max(
                (i + 1) * int(key in qnode.name().lower())
                for i, key in enumerate(["input", "livemap"])
            )
            is_layer_raster = (
                is_layer
                and cast(QgsLayerTreeLayer, qnode).layer().type()
                == Qgis.LayerType.Raster
            )
            order_point = (
                initial_order
                + mapmaking_order * 10
                + project_order * 20
                + int(is_group) * 50
                + int(is_layer_raster) * 100
            )
            self.cache[qnode_key] = order_point
        print(qnode.name(), order_point)
        return order_point


class LayerSorter:
    def __init__(self):
        self.cache = dict()

    def sorting_key(self, vlayer: QgsVectorLayer):
        order_point = self.cache.get(vlayer.id())
        if order_point is None:
            geom_order = ["Point", "Line", "Polygon", "Unknown"]
            layer_id_order = [
                "Unknown",
                "address",
                "place",
                "relation",
                "road",
                "topology",
                "roadtopology",
                "building",
                "carto",
                "admin",
            ]
            order_step = 50
            geom_order_map = {geom: i for i, geom in enumerate(geom_order)}
            layer_id_order_map = {
                layer_id: i for i, layer_id in enumerate(layer_id_order)
            }
            order_point = order_step * geom_order_map.get(
                vlayer.geometryType().name, geom_order_map["Unknown"]
            )
            layer_name = vlayer.name()
            layer_id = layer_name.split(" ")[0].lower()
            layer_order_point = layer_id_order_map.get(
                layer_id, layer_id_order_map["Unknown"]
            )
            order_point += layer_order_point
            self.cache[vlayer.id()] = order_point
        print(vlayer.id(), order_point)
        return order_point
