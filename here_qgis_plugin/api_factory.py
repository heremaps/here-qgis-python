###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

"""
Utilities to create API and credential for UI and processing toolbox

Examples:
    + To create MapMakingAPI from UI ::

        api = create_create_api_for_ui(MapMakingAPI, project_hrn="some_project_hrn")

    + To prepare credential to call processing function from UI ::

        params = {
            "HERE_CREDENTIALS_FILE": get_processing_here_cred_path_for_ui(),
            "project_hrn": project_hrn,
        }

        algorithm_id = "here_qgis_processing:IMLBatchLoad"
        algorithm = QgsApplication.processingRegistry().algorithmById(algorithm_id)

        task = QgsProcessingAlgRunnerTask(algorithm, params, context, feedback)
        task.executed.connect(on_task_completed)  # custom callback

        QgsApplication.taskManager().addTask(task)

    + To create MapMakingAPI from processing toolbox ::

        here_cred_path = parameters.get("HERE_CREDENTIALS_FILE", "")
        api = create_api_for_processing(
            MapMakingAPI, here_cred_path, project_hrn="some_project_hrn"
        )

"""

from typing import Type, TypeVar

from here_qgis.amplitude_events.amplitude_client import QgisAmplitude
from here_qgis.amplitude_events.api_usage_event import APIUsageEvent
from here_qgis.api.api import API

from .ui.here_iml.error_msg import show_error_msg_box
from .ui.utils.settings_manager import get_credential_path, get_sso_token

T = TypeVar("T", bound=API)


def _track_amplitude_event(api: API, api_type: str):
    if api:
        try:
            caller_hrn = api.get_caller_hrn()
        except Exception:
            caller_hrn = None
        user_id = "Anonymous_User" if caller_hrn is None else caller_hrn
        api_event = APIUsageEvent(
            user_id=user_id,
            event_properties={"api_type": api_type},
        )
        amplitude = QgisAmplitude()
        amplitude.track(api_event)


def create_api_for_ui(api_class: Type[T], project_hrn: str = None) -> T:
    """
    For UI functions, API object is created with SSO token from UI.
    If not set, it will try to use app credential file from UI.
    If both are not set, show error message box

    Args:
        api_class: API subclass
        project_hrn: optional

    Returns:
        API instance
    """

    token = get_sso_token()
    here_cred_path = get_credential_path()
    api = None
    if token:
        api = api_class(token=get_sso_token(), project_hrn=project_hrn)
    elif here_cred_path:
        api = api_class(here_cred_path, project_hrn=project_hrn)
    else:
        show_error_msg_box(
            ValueError("User not logged in"),
            parent=None,
            details=dict(token=token, here_cred_path=here_cred_path),
        )
    _track_amplitude_event(api, "UI")
    return api


def get_processing_here_cred_path_for_ui() -> str:
    """
    Get here credentials file for processing toolbox functions triggered by UI

    If SSO token from UI login is set, it will return empty string.
    Otherwise, it will try to use app credential file from UI.

    Returns: here_cred_path

    """
    token = get_sso_token()
    if token:
        return ""
    return get_credential_path()


def create_api_for_processing(
    api_class: Type[T], here_cred_path: str, project_hrn: str = None
) -> T:
    """
    For processing toolbox, API object is created with app credential
    if `here_cred_path` is valid, otherwise it shall try to use SSO token from UI

    Args:
        api_class: API subclass
        here_cred_path: here_cred_path must be provided explicitly
        project_hrn: optional

    Returns:
        API instance

    Raises:
        ValueError: if here_cred_path not provided and user not logged in via UI
    """

    token = get_sso_token()
    api = None
    if here_cred_path:
        api = api_class(here_cred_path, project_hrn=project_hrn)
    elif token:
        api = api_class(token=get_sso_token(), project_hrn=project_hrn)
    else:
        raise ValueError(
            "App or user credential not provided",
            dict(token=token, here_cred_path=here_cred_path),
        )
    _track_amplitude_event(api, "Processing toolbox")
    return api
