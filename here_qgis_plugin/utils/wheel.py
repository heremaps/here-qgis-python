###############################################################################
#
# Copyright (c) 2026 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os
from typing import Dict, Optional, TypedDict, Union

from ..config import WHEEL_DIR

WHEEL_PACKAGES = ["here_qgis[here-vml]"]

# deprecated in favor of find-links


class WheelInfo(TypedDict):
    name: str
    version: str
    file: Optional[str]


def get_all_wheel_files(wheel_path) -> Dict[str, WheelInfo]:
    os.makedirs(wheel_path, exist_ok=True)

    def parse_wheel_filename(filename: str) -> WheelInfo:
        parts = filename.split(".")[0].split("-")
        return {
            "name": parts[0],
            "version": parts[1],
            "file": os.path.join(wheel_path, filename),
        }

    return {
        info["name"]: info
        for info in map(
            parse_wheel_filename,
            filter(
                lambda file: file.endswith(".whl") or file.endswith(".tar.gz"),
                os.listdir(wheel_path),
            ),
        )
    }


WHEEL_FILES = get_all_wheel_files(WHEEL_DIR)


def get_package_name(package_str):
    """Get package name from package string, e.g. package[extras]"""
    return package_str.split("[")[0]


def get_wheel_info(package) -> WheelInfo:
    package_name = get_package_name(package)
    return WHEEL_FILES.get(package_name, {})


def get_wheel_file_or_package_str(
    package: str, wheel_info: WheelInfo
) -> Union[str, WheelInfo]:
    package_name = get_package_name(package)
    resolved = wheel_info.get("file", package_name)
    return package.replace(package_name, resolved)


def packages_to_wheel_files(packages):
    package_files = []
    for package in packages:
        package_info = get_wheel_info(package)
        if package in WHEEL_PACKAGES and not package_info:
            raise Exception(f"Wheel file not found for {package}")
        package_file = get_wheel_file_or_package_str(package, package_info)
        package_files.append(package_file)
    return package_files
