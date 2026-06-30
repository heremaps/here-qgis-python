###############################################################################
#
# Copyright (c) 2023 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = "$Format:%H$"

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .processing_toolbox import (
    AlignV1,
    ApplyStyleToIML,
    ApplyStyleToManyIMLs,
    BatchLoadVersionedLayer,
    ClearTmpDir,
    FlattenOnFly,
    IMLBatchLoad,
    IMLFlattenToCSV,
    IMLLoadAndFlatten,
    IMLUnflattenCSV,
    IMLUnflattenOnTheFly,
    LoadBasemap,
    LoadIMLayer,
    LoadIMLayerDensity,
    LoadOSMLayer,
    LoadPartitionVersionedLayer,
    LoadQueryVersionedLayer,
    LoadVersionedLayer,
    MapMakingUpload,
    MomSyntaxChecker,
    OnDemandProcess,
    OneClickStyleIML,
    ProcessGeocoding,
    ProcessRouting,
    QueryAllAttributes,
    RefreshToken,
    ReloadAllVisibleLayers,
    ReloadIMLayer,
    ReloadManyIMLLayers,
    Settings,
)
from .ui.icons import icon_logo


class HereQgisPluginProvider(QgsProcessingProvider):
    def __init__(self):
        """
        Default constructor.
        """
        QgsProcessingProvider.__init__(self)

    def unload(self):
        """
        Unloads the provider. Any tear-down steps required by the provider
        should be implemented here.
        """
        pass

    def loadAlgorithms(self):
        """
        Loads all algorithms belonging to this provider.
        """
        self._add_algorithm(Settings())
        self._add_algorithm(LoadBasemap())
        self._add_algorithm(LoadIMLayer())
        self._add_algorithm(ProcessRouting())
        self._add_algorithm(ProcessGeocoding())
        self._add_algorithm(IMLBatchLoad())
        self._add_algorithm(LoadIMLayerDensity())
        self._add_algorithm(LoadVersionedLayer())
        self._add_algorithm(LoadPartitionVersionedLayer())
        self._add_algorithm(BatchLoadVersionedLayer())
        self._add_algorithm(MapMakingUpload())
        self._add_algorithm(RefreshToken())
        self._add_algorithm(ApplyStyleToIML())
        self._add_algorithm(ApplyStyleToManyIMLs())
        self._add_algorithm(OneClickStyleIML())
        self._add_algorithm(ReloadIMLayer())
        self._add_algorithm(ReloadManyIMLLayers())
        self._add_algorithm(IMLFlattenToCSV())
        self._add_algorithm(IMLUnflattenCSV())
        self._add_algorithm(IMLLoadAndFlatten())
        self._add_algorithm(FlattenOnFly())
        self._add_algorithm(AlignV1())
        self._add_algorithm(OnDemandProcess())
        self._add_algorithm(IMLUnflattenOnTheFly())
        self._add_algorithm(MomSyntaxChecker())
        self._add_algorithm(ReloadAllVisibleLayers())
        self._add_algorithm(LoadQueryVersionedLayer())
        self._add_algorithm(QueryAllAttributes())
        self._add_algorithm(ClearTmpDir())
        self._add_algorithm(LoadOSMLayer())

    def _add_algorithm(self, algorithm):
        if not self.addAlgorithm(algorithm):
            raise RuntimeError(f"Failed to add algorithm: {algorithm.id()}")

    def id(self):
        """
        Returns the unique provider id, used for identifying the provider. This
        string should be a unique, short, character only string, eg "qgis" or
        "gdal". This string should not be localised.
        """
        return "here_qgis_processing"

    def name(self):
        """
        Returns the provider name, which is used to describe the provider
        within the GUI.

        This string should be short (e.g. "Lastools") and localised.
        """
        return self.tr("HERE QGIS Processing")

    def icon(self):
        """
        Should return a QIcon which is used for your provider inside
        the Processing toolbox.
        """
        return QIcon(icon_logo)

    def longName(self):
        """
        Returns the a longer version of the provider name, which can include
        extra details such as version numbers. E.g. "Lastools LIDAR tools
        (version 2.2.1)". This string should be localised. The default
        implementation returns the same string as name().
        """
        return self.name()
