###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from typing import List, Optional

from qgis.core import QgsMessageLog
from qgis.PyQt.QtCore import QObject, QRunnable, pyqtSignal

from here_qgis.api.mapmaking import MapMakingAPI, ViolationLayerFeature

from ..ui.utils.settings_manager import get_sso_token


class SyntaxSignal(QObject):
    taskCompleted = pyqtSignal(int)


class MOMSyntaxCheckerAndPurge(QRunnable):
    def __init__(
        self,
        catalog_hrn: str,
        layers_ids: List[str],
        credentials: Optional[str],
        project_hrn: Optional[str],
        purge_after_checker=False,
    ):
        super().__init__()
        self.signal = SyntaxSignal()

        if credentials:
            self.mm = MapMakingAPI(here_cred_path=credentials, project_hrn=project_hrn)
        else:
            self.mm = MapMakingAPI(token=get_sso_token(), project_hrn=project_hrn)

        self.purge_after_checker = purge_after_checker
        self.catalog_hrn = catalog_hrn
        self.layers_ids = layers_ids

    # TODO: only one layer or many layers?
    # I would stay with many layers, since user could have uploaded
    # to many layers and then run syntax checker
    def run(self):
        # run mom syntax checker and wait for finish
        QgsMessageLog.logMessage("MOM Syntax Checker and Purge running...")
        operations = [("momToSyntaxChecker", {})]
        self.mm.ondemand_process(operations)
        _, operation_state = self.mm.check_operation_states()
        operation_state = operation_state["momToSyntaxChecker"]
        if operation_state != "completed":
            self.signal.taskCompleted.emit(4)
            return False

        layers_with_violation = []

        for layer_id in self.layers_ids:
            statistics = self.mm.get_statistics(
                self.catalog_hrn, f"{layer_id}-violation"
            )
            if statistics.get_count() > 0:
                layers_with_violation.append(layer_id)
                # break

        if len(layers_with_violation) > 0:
            QgsMessageLog.logMessage(
                "Layers violating MOM Syntax Checker rules:"
                f" {', '.join(layers_with_violation)}"
            )
            if not self.purge_after_checker:
                self.signal.taskCompleted.emit(3)
                return True
        else:
            QgsMessageLog.logMessage("Layers don't violate MOM Syntax Checker")
            self.signal.taskCompleted.emit(2)
            return True

        QgsMessageLog.logMessage("MOM Syntax checker finished")
        if self.purge_after_checker and len(layers_with_violation) > 0:
            QgsMessageLog.logMessage("MOM Syntax Checker finished. Purge in progress")

            # run deletes
            violation_ids = []
            feature_ids = []
            for layer_id in layers_with_violation:
                QgsMessageLog.logMessage(f"Start deleting features from {layer_id}")
                violations = self.mm.get_violation_layer(self.catalog_hrn, layer_id)
                curr_features = violations.get_features()
                syntaxed: List[ViolationLayerFeature] = list(
                    filter(
                        lambda f: f.get_rule_id() == "MOM_SCHEMA_VIOLATION",
                        curr_features,
                    )
                )
                v_ids = [f.get_violation_id() for f in syntaxed]
                f_ids = []
                for f in syntaxed:
                    f_ids.extend(f.get_references_ids())
                violation_ids.extend(v_ids)
                feature_ids.extend(f_ids)

                # delete from input
                if not self.mm.delete_features(self.catalog_hrn, layer_id, feature_ids):
                    self.signal.taskCompleted.emit(5)
                    return False
                # delete from violation
                if not self.mm.delete_features(
                    self.catalog_hrn, f"{layer_id}-violation", violation_ids
                ):
                    self.signal.taskCompleted.emit(5)
                    return False
                QgsMessageLog.logMessage(f"Finished deleting features from {layer_id}")

        self.signal.taskCompleted.emit(1)
        return True
