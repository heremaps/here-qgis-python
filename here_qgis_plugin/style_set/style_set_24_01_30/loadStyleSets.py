###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

# flake8: noqa

############################################################################
##################  usage & settings #######################################
############################################################################

# 1. If necessary adjust below styleSetRootDirectory
# !!! by using unix conform slashes --> '/' !!!!!!!!!!!!
#
styleSetRootDirectory = "c:/style_set_24_01_30"


# 2. Addjust below catalogName
#
catalogName = "YOUR LOADED CATALOG"
# Example catalogName = 'here-stable-2401'

# 3. If necessary adjust below styleSet (default is Standard others are listed below)

styleSetPath = styleSetRootDirectory + "/" + "Standard"
# styleSetPath = styleSetRootDirectory + '/' + 'Standard Color compare/blue'
# styleSetPath = styleSetRootDirectory + '/' + 'Standard Color compare/red'

# 4. execute script by click on the green execution button

############################################################################
##################  END usage & settings ###################################
############################################################################

from qgis.core import QgsProject

layers = iface.mapCanvas().layers()

layerCount = 0

for layer in layers:
    layerCount = layerCount + 1
    print(layer.name())
    layer = QgsProject.instance().mapLayersByName(layer.name())[0]
    iface.setActiveLayer(layer)

    if layer.name() == catalogName + "-Address Layer-address-Point-0":
        layer.loadNamedStyle(styleSetPath + "/" + "address.qml")
        print("  style loaded  " + layer.name())
        layer.triggerRepaint()

    if layer.name() == catalogName + "-Place Layer-place-Point-0":
        layer.loadNamedStyle(styleSetPath + "/" + "place.qml")
        print("  style loaded  " + layer.name())
        layer.triggerRepaint()

    if layer.name() == catalogName + "-Sign Layer-sign-Point-0":
        layer.loadNamedStyle(styleSetPath + "/" + "sign.qml")
        print("  style loaded  " + layer.name())
        layer.triggerRepaint()

    if layer.name() == catalogName + "-Lane Layer-lane-LineString-0":
        layer.loadNamedStyle(styleSetPath + "/" + "lane.qml")
        print("  style loaded  " + layer.name())
        layer.triggerRepaint()

    if layer.name() == catalogName + "-Topology Layer-topology-LineString-0":
        layer.loadNamedStyle(styleSetPath + "/" + "topology.qml")
        print("  style loaded  " + layer.name())
        layer.triggerRepaint()

    if layer.name() == catalogName + "-Relation Layer-relation-MultiPoint-0":
        layer.loadNamedStyle(styleSetPath + "/" + "relation.qml")
        print("  style loaded  " + layer.name())
        layer.triggerRepaint()

    if layer.name() == catalogName + "-Building Layer-building-MultiPolygon-0":
        layer.loadNamedStyle(styleSetPath + "/" + "building.qml")
        print("  style loaded  " + layer.name())
        layer.triggerRepaint()

    if layer.name() == catalogName + "-Carto Layer-carto-MultiLineString-0":
        layer.loadNamedStyle(styleSetPath + "/" + "cartoLine.qml")
        print("  style loaded  " + layer.name())
        layer.triggerRepaint()

    if layer.name() == catalogName + "-Carto Layer-carto-MultiPolygon-0":
        layer.loadNamedStyle(styleSetPath + "/" + "cartoPolygon.qml")
        print("  style loaded  " + layer.name())
        layer.triggerRepaint()

    if layer.name() == catalogName + "-Admin Layer-admin-MultiPolygon-0":
        layer.loadNamedStyle(styleSetPath + "/" + "admin.qml")
        print("  style loaded  " + layer.name())
        layer.triggerRepaint()


print("layerCount: " + str(layerCount))
