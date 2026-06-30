###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import json
import os
from datetime import datetime
from typing import Union

from qgis.core import QgsSettings

from here_qgis.platform.platform_auth import PlatformAuth
from here_qgis.platform.platform_credentials import Credentials

# Settings Keys
SETTINGS_PREFIX = "here_qgis_plugin/ui"
SETTINGS_CRED_PATH = "here_qgis_plugin/ui/credential_path"
SETTINGS_AUTH_STATUS = "here_qgis_plugin/ui/authenticated"
SETTINGS_FLATTEN_CONFIG_PATH = "here_qgis_plugin/ui/flatten_config_file/path"
SETTINGS_TOKEN_JSON = "here_qgis_plugin/ui/token_json"
SETTINGS_FALLBACK_TOKEN = "here_qgis_plugin/ui/fallback_token"
SETTINGS_PLUGIN_ALREADY_INSTALLED = "here_qgis_plugin/already_installed"


def get_already_installed():
    return QgsSettings().value(SETTINGS_PLUGIN_ALREADY_INSTALLED, False, type=bool)


def set_already_installed():
    QgsSettings().setValue(SETTINGS_PLUGIN_ALREADY_INSTALLED, True)


# Credential Path Management
def get_credential_path():
    return QgsSettings().value(SETTINGS_CRED_PATH, "")


def save_credential_path(path):
    QgsSettings().setValue(SETTINGS_CRED_PATH, path)
    set_auth_status(True)


def clear_credential_path():
    QgsSettings().remove(SETTINGS_CRED_PATH)
    set_auth_status(False)


# Configuration preset Management
def get_config_preset_path():
    return QgsSettings().value(SETTINGS_FLATTEN_CONFIG_PATH, "")


def save_config_preset_path(path):
    QgsSettings().setValue(SETTINGS_FLATTEN_CONFIG_PATH, path)


def clear_config_preset_path():
    QgsSettings().remove(SETTINGS_FLATTEN_CONFIG_PATH)


def is_valid_config_path():
    config_path = get_config_preset_path()
    if not config_path:
        return False
    if not os.path.exists(config_path):
        return False
    if not os.path.isfile(config_path):
        return False
    return True


# Authentication Status Management
def set_auth_status(value):
    """Set authentication status."""
    QgsSettings().setValue(SETTINGS_AUTH_STATUS, bool(value))


def get_auth_status():
    """Check authentication status."""
    return QgsSettings().value(SETTINGS_AUTH_STATUS, "", type=bool)


def is_authenticated():
    return get_auth_status()


# Token Management
def get_app_token():
    """Retrieve a new authentication token each time."""
    file_path = get_credential_path()
    if not file_path:
        set_auth_status(False)
        return None

    if not os.path.exists(file_path):
        set_auth_status(False)
        clear_credential_path()
        return None

    try:
        platform_cred = Credentials.from_credentials_file(file_path)
        platform = PlatformAuth(platform_cred)
        token = platform.token
        if token:
            set_auth_status(True)
            return token
    except Exception as e:
        set_auth_status(False)
        clear_credential_path()
        print(f"Authentication failed: {e}")

    return None


def _get_info_from_token(token_json: Union[str, dict], key: str) -> str:
    """
    Parse given key from json string

    Args:
        token_json: can be json string, or dict (due to QGIS auto type casting)
        key: key from which get the data if token_json is dict

    Returns:
        token

    """
    if not token_json:
        return ""

    token_data = None
    if isinstance(token_json, dict):
        token_data = token_json
    elif isinstance(token_json, str):
        try:
            token_data = json.loads(token_json)
        except Exception as e:
            print("Failed to parse token:", e)

    if token_data and isinstance(token_data, dict):
        token = token_data.get(key)
        if token:
            return token

    return ""


def parse_sso_token_json(token_json: Union[str, dict]) -> str:
    """
    Parse access token from json string

    Args:
        token_json: can be json string, or dict (due to QGIS auto type casting)

    Returns:
        token

    """
    return _get_info_from_token(token_json, "accessToken")


def get_sso_token_expiration() -> str:
    """
    Get expiration date of token from token json.

    Returns:
        expiration date

    """
    token_json = QgsSettings().value(SETTINGS_TOKEN_JSON, "")
    return _get_info_from_token(token_json, "accessTokenExpires")


def get_sso_refresh_token_expiration() -> str:
    """
    Get expiration date of refresh token from token json.

    Returns:
        refresh expiration date

    """
    token_json = QgsSettings().value(SETTINGS_TOKEN_JSON, "")
    return _get_info_from_token(token_json, "refreshTokenExpires")


def get_sso_token():
    """
    Retrieve and parse sso access token from QGIS settings.
    If not set, then try to get fallback sso access token from QGIS settings.

    Returns None if both are not set.
    """
    token_json = QgsSettings().value(SETTINGS_TOKEN_JSON, "")
    token = parse_sso_token_json(token_json)
    if token:
        return token
    return QgsSettings().value(SETTINGS_FALLBACK_TOKEN, None)


def parse_time(time: str):
    time = time[:-1] if time[-1] == "Z" else time
    return datetime.fromisoformat(time)


def token_expired(exp: str = "access"):
    curr_time = datetime.now()
    if exp == "access":
        expiration = get_sso_token_expiration()
    elif exp == "refresh":
        expiration = get_sso_refresh_token_expiration()
    else:
        raise ValueError("Invalid expiration time")
    if expiration:
        expiration = parse_time(expiration)
        if expiration <= curr_time:
            return True
        return False
    return False  # not exactly expired - it doesnt even exist


def set_sso_token_json(response: str):
    """
    Store the sso token json response into QGIS settings.
    """
    QgsSettings().setValue(SETTINGS_TOKEN_JSON, response)
    # TODO: set_auth_status only valid sso token
    set_auth_status(True)


def clear_sso_token():
    QgsSettings().remove(SETTINGS_TOKEN_JSON)
    QgsSettings().remove(SETTINGS_FALLBACK_TOKEN)
    set_auth_status(False)


def set_fallback_sso_token(token: str):
    """Store fallback access token value into QGIS settings."""
    QgsSettings().setValue(SETTINGS_FALLBACK_TOKEN, token)
    set_auth_status(True)
