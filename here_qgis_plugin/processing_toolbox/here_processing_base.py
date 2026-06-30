# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import typing
from abc import abstractmethod
from typing import Any, Dict

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingParameterEnum,
)
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from typing_extensions import deprecated

from ..ui.icons import icon_logo
from ..ui.utils.settings_manager import get_sso_token
from .processing_utils import bbox_from_extent


class HereProcessingException(QgsProcessingException):
    ...


class HereProcessingAlgorithm(QgsProcessingAlgorithm):
    @classmethod
    @abstractmethod
    def createInstance(cls) -> "HereProcessingAlgorithm":
        return cls()

    @abstractmethod
    def displayName(self) -> str:
        return self.tr(self.name())

    def name(self) -> str:
        return self.__class__.__name__

    def icon(self):
        return QIcon(icon_logo)

    def group(self):
        return ""

    def groupId(self):
        return ""

    @staticmethod
    def tr(text: str) -> str:
        return QCoreApplication.translate("HereProcessingAlgorithm", text)

    # def flags(self):
    #     return super().flags() | QgsProcessingAlgorithm.FlagNoThreading

    @abstractmethod
    def initAlgorithm(self, configuration: Dict[str, Any] = None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """
        raise NotImplementedError()

    @abstractmethod
    def processAlgorithm(
        self,
        parameters: Dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> Dict[str, Any]:
        """
        HERE is where the processing itself takes place.
        """
        raise NotImplementedError()
        return {"output": "dummy"}

    def get_bbox_from_params(
        self,
        parameters: Dict[str, Any],
        parameter_name: str,
        context: QgsProcessingContext,
    ):
        """
        Get bounding box from extent

        """
        extent = self.parameterAsExtent(
            parameters,
            parameter_name,
            context,
            crs=QgsCoordinateReferenceSystem("EPSG:4326"),
        )

        return bbox_from_extent(extent)

    @staticmethod
    def error(feedback: QgsProcessingFeedback, error_msg: str, log_level="error"):
        feedback.reportError("{}: {}".format(log_level.upper(), error_msg))

    @classmethod
    def warn(cls, feedback: QgsProcessingFeedback, error_msg: str):
        cls.error(feedback, error_msg, "warn")

    def _check_invalid_credentials(
        self, parameters: Dict[str, Any], feedback: QgsProcessingFeedback
    ):
        if not (parameters.get("HERE_CREDENTIALS_FILE", "") or get_sso_token()):
            msg = "No credentials found! Use credentials file or login with SSO."
            feedback.pushWarning(msg)
            return {
                "success": False,
                "message": msg,
            }
        return {}


@deprecated("Use QgsProcessingParameterEnum instead")
class HereProcessingEnum(QgsProcessingParameterEnum):
    def checkValueIsAcceptable(
        self, input: typing.Any, context: typing.Optional[QgsProcessingContext] = ...
    ) -> bool:
        return hasattr(input, "__iter__") and (
            all(isinstance(i, int) for i in input)
            or all(isinstance(i, str) for i in input)
        )
