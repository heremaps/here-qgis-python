###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from functools import partial

from qgis.core import QgsApplication, QgsProcessingAlgRunnerTask

from ...api_factory import get_processing_here_cred_path_for_ui


def refresh_token_processing(
    context,
    feedback,
    on_reload_completed,
):
    params = {"HERE_CREDENTIALS_FILE": get_processing_here_cred_path_for_ui()}

    algorithm_id = "here_qgis_processing:RefreshToken"
    algorithm = QgsApplication.processingRegistry().algorithmById(algorithm_id)

    task = QgsProcessingAlgRunnerTask(algorithm, params, context, feedback)
    task.executed.connect(partial(on_reload_completed, context))
    QgsApplication.taskManager().addTask(task)
