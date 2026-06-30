###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.core import (
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterString,
)

from ..settings import (
    UIToolbarsSetting,
    clear_catalog_hrn,
    clear_path,
    clear_project_hrn,
    clear_vml_catalog_hrn,
    get_catalog_hrn,
    get_path,
    get_project_hrn,
    get_vml_catalog_hrn,
    save_catalog_hrn,
    save_path,
    save_project_hrn,
    save_vml_catalog_hrn,
)
from .here_processing_base import HereProcessingAlgorithm


class Settings(HereProcessingAlgorithm):
    @classmethod
    def createInstance(cls) -> "HereProcessingAlgorithm":
        return cls()

    def displayName(self) -> str:
        return "Util: HERE Processing Toolbox Settings"

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """
        # HERE credentials.properties, it should be without scope (11.03.2024)
        self.addParameter(
            QgsProcessingParameterFile(
                "HERE_CREDENTIALS_FILE",
                "Specify HERE credentials file",
                behavior=QgsProcessingParameterFile.Behavior.File,
                fileFilter="All Files (*.*)",
                defaultValue=get_path(),
                optional=True,
            )
        )

        # project hrn
        self.addParameter(
            QgsProcessingParameterString(
                "project_hrn",
                "Specify Project HRN",
                multiLine=False,
                defaultValue=get_project_hrn(),
                optional=True,
            )
        )

        # catalog hrn
        self.addParameter(
            QgsProcessingParameterString(
                "catalog_hrn",
                "Specify catalog:hrn",
                multiLine=False,
                defaultValue=get_catalog_hrn(),
                optional=True,
            )
        )

        # VML
        self.addParameter(
            QgsProcessingParameterString(
                "vml_catalog_hrn",
                "Specify VML catalog HRN",
                multiLine=False,
                defaultValue=get_vml_catalog_hrn(),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                "ui_toolbars_default_key",
                "UI: Toolbars default key",
                usesStaticStrings=True,
                allowMultiple=False,
                options=UIToolbarsSetting.OPTIONS,
                defaultValue=UIToolbarsSetting.get_value(None),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                "unset",
                "Clear settings",
                defaultValue=False,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        HERE is where the processing itself takes place.
        """
        unset = parameters.get("unset", False)
        if unset:
            clear_project_hrn()
            clear_path()
            clear_catalog_hrn()
            clear_vml_catalog_hrn()
            UIToolbarsSetting.clear_value()
            feedback.pushInfo("Settings cleared")
            return {}

        file_path = parameters.get("HERE_CREDENTIALS_FILE", None)
        project_hrn = parameters.get("project_hrn", "")
        catalog_hrn = parameters.get("catalog_hrn", "")
        vml_catalog_hrn = parameters.get("vml_catalog_hrn", "")
        ui_toolbars_default_key = parameters.get("ui_toolbars_default_key", "")

        save_path(file_path)
        save_project_hrn(project_hrn)
        save_catalog_hrn(catalog_hrn)
        save_vml_catalog_hrn(vml_catalog_hrn)
        UIToolbarsSetting.save_value(ui_toolbars_default_key)

        feedback.pushInfo("Settings saved")
        return {}
