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

from here_qgis.api.mapmaking import MapMakingAPI

from ..api_factory import create_api_for_processing
from ..settings import get_path, get_project_hrn
from .here_processing_base import HereProcessingAlgorithm


class OnDemandProcess(HereProcessingAlgorithm):
    @classmethod
    def createInstance(cls):
        return cls()

    def displayName(self) -> str:
        return "MM: On demand process (mapmaking)"

    def __init__(self):
        super().__init__()
        self.conflation_profiles = [
            "",
            "3rd_party_data",
            "merge_map",
            "ground_truth_geo_only",
        ]
        self.validateRepair_profiles = ["autoRepairEnabled", "wavEnable"]
        self.validateRepair_profiles_full = [
            "Repair violations",
            "Wide Area Validation",
        ]

    def initAlgorithm(self, configuration=None):
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

        self.addParameter(
            QgsProcessingParameterString(
                "project_hrn",
                "Specify Project HRN",
                multiLine=False,
                defaultValue=get_project_hrn(),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                "conflateOnDemand",
                "Enable Conflation On-Demand (profile has to be selected)",
                options=self.conflation_profiles,
                allowMultiple=False,
                usesStaticStrings=False,
                defaultValue=[],
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                "validateRepairOnDemand",
                "Validation & Repair On-Demand",
                options=self.validateRepair_profiles_full,
                allowMultiple=True,
                usesStaticStrings=False,
                defaultValue=[],
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                "momToSyntaxChecker",
                "Enable MOM Syntax Checker",
                defaultValue=False,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        here_cred_path = parameters.get("HERE_CREDENTIALS_FILE", "")
        map_making = create_api_for_processing(
            MapMakingAPI, here_cred_path, project_hrn=parameters["project_hrn"]
        )

        operations = []
        output = {}
        if parameters["conflateOnDemand"]:
            operations.append(
                (
                    "conflateOnDemand",
                    {
                        "profile": self.conflation_profiles[
                            parameters["conflateOnDemand"]
                        ]
                    },
                )
            )

        if parameters["validateRepairOnDemand"]:
            # Create dictionary with all keys set to False by default
            validateRepairOnDemand_profile = {
                key: False for key in self.validateRepair_profiles
            }

            # Update dictionary based on indices to set corresponding keys to True
            for index in parameters["validateRepairOnDemand"]:
                if index < len(self.validateRepair_profiles):
                    validateRepairOnDemand_profile[
                        self.validateRepair_profiles[index]
                    ] = True

            operations.append(
                ("validateRepairOnDemand", validateRepairOnDemand_profile)
            )

        if parameters["momToSyntaxChecker"]:
            operations.append(("momToSyntaxChecker", {}))

        if operations:
            map_making.ondemand_process(operations)
            output["operations"] = operations
            output["states"] = map_making.next_actions
            for operation in operations:
                if output["states"][operation[0]] == "failed":
                    feedback.reportError(f"operation {operation[0]} failed")

        output["success"] = True
        return output
