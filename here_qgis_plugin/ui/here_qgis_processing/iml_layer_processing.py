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


def iml_layer_processing(
    project_hrn,
    catalog_hrn,
    layer_id,
    extent_str,
    style_set,
    file_type,
    context,
    feedback,
    on_task_completed,
    catalog_type=None,
    iml_context=0,
    query="",
):
    """Loads an IML layer into a GeoPackage
    asynchronously using HERE QGIS Processing."""

    # Prepare parameters
    params = {
        "HERE_CREDENTIALS_FILE": get_processing_here_cred_path_for_ui(),
        "project_hrn": project_hrn,
        "catalog_hrn": catalog_hrn,
        "iml_layers": layer_id,
        "extent": extent_str,
        "style_set": style_set,
        "file_type": file_type,
        "iml_context": iml_context,
        "query": query,
    }

    # Retrieve the algorithm object from the registry
    algorithm_id = "here_qgis_processing:IMLBatchLoad"
    algorithm = QgsApplication.processingRegistry().algorithmById(algorithm_id)

    # Create the processing task
    task = QgsProcessingAlgRunnerTask(algorithm, params, context, feedback)

    task.executed.connect(partial(on_task_completed, context, params, catalog_type))
    # Add the task to QGIS's task manager
    QgsApplication.taskManager().addTask(task)
