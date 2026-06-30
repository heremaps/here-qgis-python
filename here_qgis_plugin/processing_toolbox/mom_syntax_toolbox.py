###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFile,
    QgsProcessingParameterString,
)
from qgis.PyQt.QtCore import Qt, QThreadPool
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.utils import iface

from ..settings import get_path, get_project_hrn
from .here_processing_base import HereProcessingAlgorithm
from .mom_syntax_checker_purge import MOMSyntaxCheckerAndPurge


def pop_up_message(title: str, text: str):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg.setWindowModality(Qt.WindowModality.ApplicationModal)
    msg.show()


def pop_up_message_violation_purge():
    pop_up_message(
        "MOMSyntaxCheckerAndPurge Completed",
        """MOMSyntaxCheckerAndPurge has finished executing!
        Layers with violations have been purged""",
    )


def pop_up_message_fail():
    pop_up_message(
        "MOMSyntaxCheckerAndPurge finished with error",
        """MOM Syntax Checker has finished but with incorrect status.
        Features will not be purged""",
    )


def pop_up_message_no_violations():
    pop_up_message(
        "MOMSyntaxCheckerAndPurge Completed",
        "Layers don't violate MOM Syntax Checker",
    )


def pop_up_message_violation_no_purge():
    pop_up_message(
        "MOMSyntaxCheckerAndPurge Completed",
        "Layers violate MOM Syntax Checker. Will not purge",
    )


def pop_up_message_delete_failed():
    pop_up_message(
        "MOMSyntaxCheckerAndPurge finished with error",
        """Deletion finished with error. Not all features were deleted""",
    )


def signal_message(status: int):
    if status == 1:
        pop_up_message_violation_purge()
    elif status == 2:
        pop_up_message_no_violations()
    elif status == 3:
        pop_up_message_violation_no_purge()
    elif status == 4:
        pop_up_message_fail()
    else:
        pop_up_message_delete_failed()


class MomSyntaxChecker(HereProcessingAlgorithm):
    @classmethod
    def createInstance(cls):
        return cls()

    def displayName(self) -> str:
        return "MM: MOM syntax checker and purge"

    def flags(self):
        return super().flags() | self.Flag.FlagNoThreading

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
            QgsProcessingParameterString(
                "catalog_hrn",
                "Specify Catalog HRN",
                multiLine=False,
                defaultValue=(
                    "hrn:here:data::olp-here:qgispluginproject-input-1745313455114"
                ),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                "purge_failed",
                "Purge layers",
                defaultValue=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                "layers", "Layers to purge (comma-separated, non-space)", optional=True
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        purge = parameters["purge_failed"]
        layers = parameters["layers"]
        if purge and layers == "":
            QgsMessageLog.logMessage("Provide layers ids if you want to purge")
            return {}
        layers = list(map(lambda layer: layer.strip(), layers.split(",")))

        mscp = MOMSyntaxCheckerAndPurge(
            parameters["catalog_hrn"],
            layers,
            parameters.get("HERE_CREDENTIALS_FILE", ""),
            parameters["project_hrn"],
            purge,
        )
        thread_pool = QThreadPool.globalInstance()
        mscp.signal.taskCompleted.connect(signal_message)

        thread_pool.start(mscp)
        if iface:
            iface.messageBar().pushMessage(
                "MOM Syntax Checker and Purge performing in the background",
                level=Qgis.MessageLevel.Info,
                duration=5,
            )

        return {"task": mscp}
