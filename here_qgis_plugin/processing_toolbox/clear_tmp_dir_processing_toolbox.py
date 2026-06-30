# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2026 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.core import QgsProcessingParameterBoolean

from ..utils.clear_tmp import clear_tmp_directory
from .here_processing_base import HereProcessingAlgorithm


class ClearTmpDir(HereProcessingAlgorithm):
    @classmethod
    def createInstance(cls) -> "HereProcessingAlgorithm":
        return cls()

    def displayName(self) -> str:
        return "Util: Clean Temporary Data Directory"

    def initAlgorithm(self, configuration=None):
        self.addParameter(
            QgsProcessingParameterBoolean(
                "clear_tmp_dir",
                "Clear Temporary Data Directory",
                defaultValue=False,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        clear_tmp_dir = self.parameterAsBool(parameters, "clear_tmp_dir", context)

        if clear_tmp_dir:
            try:
                clear_tmp_directory()
                feedback.pushInfo("Temporary Data Directory cleared successfully")
            except Exception as e:
                feedback.reportError(str(e))
                raise

        return {
            "success": True,
        }
