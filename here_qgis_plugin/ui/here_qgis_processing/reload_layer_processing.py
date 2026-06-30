###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from functools import partial

from qgis.core import QgsApplication, QgsProcessingAlgRunnerTask, QgsProject

from ... import __version__ as PLUGIN_VERSION
from ...api_factory import get_processing_here_cred_path_for_ui


def is_MM_project():
    project = QgsProject.instance()
    metadata = project.metadata()
    author = metadata.author()
    return author == "MM_UI"


def reload_layer_processing(
    extent_str,
    context,
    feedback,
    on_task_completed,
):
    """Reloads the layer in QGIS."""

    params = {
        "HERE_CREDENTIALS_FILE": get_processing_here_cred_path_for_ui(),
        "extent": extent_str,
    }

    print(f"Reloading layers with params: {params}")

    if is_MM_project():
        project = QgsProject.instance()
        metadata = project.metadata()
        algorithm_id = "here_qgis_processing:ReloadAllVisibleLayers"
        metadata.setAuthor("here_qgis-python-{}".format(PLUGIN_VERSION))
        project.setMetadata(metadata)
        project.write()
    else:
        algorithm_id = "here_qgis_processing:ReloadManyIMLLayers"
    algorithm = QgsApplication.processingRegistry().algorithmById(algorithm_id)

    task = QgsProcessingAlgRunnerTask(algorithm, params, context, feedback)
    task.executed.connect(partial(on_task_completed, context, params))

    QgsApplication.taskManager().addTask(task)
