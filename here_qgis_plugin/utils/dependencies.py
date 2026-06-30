###############################################################################
#
# Copyright (c) 2023 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import importlib
import importlib.metadata
import logging
import os
import platform
import re
import site
import subprocess
import sys
import sysconfig
from pathlib import Path
from types import ModuleType
from typing import List, Union

from qgis.core import Qgis, QgsApplication

from ..config import PLUGIN_NAME, SHARED_LIB_DIR, WHEEL_DIR
from .cmd_exec import CmdExec, CondaExec, PipExec, PixiExec, PyExec

logger = logging.getLogger(__name__)

# module name
CORE_PACKAGE = "here_qgis"

# package string for installation
CORE_PACKAGE_STR = "here_qgis[here-vml]"
REQUIRED_PACKAGES = [CORE_PACKAGE_STR]

REGEX_PACKAGE_NAME = re.compile("^[A-Za-z0-9_-]+")


def get_package_name(package_str):
    """Get package name from package string, e.g. package[extras]"""
    return package_str.split("[")[0]


def confirm_with_dialog(
    missing_packages: List[str] = REQUIRED_PACKAGES, system_name: str = "Python"
) -> bool:
    from qgis.PyQt.QtWidgets import QMessageBox

    message = (
        f"The following {system_name} packages are required to use the plugin"
        f" {PLUGIN_NAME}:\n\n"
    )
    message += "\n".join(missing_packages)
    message += (
        "\n\nWould you like to install them now? After installation please restart"
        " QGIS."
    )

    reply = QMessageBox.question(
        None,
        "Missing Dependencies",
        message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )

    if reply == QMessageBox.StandardButton.Yes:
        return True
    return False


def install_packages_with_confirm_dialog(
    required_packages: List[str] = REQUIRED_PACKAGES,
):
    # Check if required packages are installed
    setup_lib_dir()
    setup = DependencySetup.from_os()
    packages = setup.should_install_deps(required_packages)
    if packages and confirm_with_dialog(packages):
        setup.install_packages(packages)

    ok = not setup.should_install_deps(required_packages)
    return ok


def is_module_missing(module_string: str):
    missing = False
    try:
        importlib.import_module(module_string)
    except ImportError:
        missing = True
    return missing


def is_package_missing(package: str):
    missing = False
    try:
        importlib.metadata.distribution(get_package_name(package)).metadata.get("Name")
    except importlib.metadata.PackageNotFoundError:
        missing = True
    return missing


def get_missing_packages(required_packages: List[str] = REQUIRED_PACKAGES):
    missing_packages = []
    for package in required_packages:
        if is_package_missing(package):
            missing_packages.append(package)
    return missing_packages


def is_core_package_shared_lib(mod: ModuleType) -> bool:
    return mod.__path__[0].startswith(SHARED_LIB_DIR)


def is_core_package_symlink(mod: ModuleType) -> bool:
    return mod.__path__[0].endswith(os.path.join("src", CORE_PACKAGE))


def check_core_package_location() -> bool:
    """Return True if core package does not need updates, based on its location.
    Return False otherwise.
    """
    try:
        mod = importlib.import_module(CORE_PACKAGE)
        print(mod.__path__)
        return is_core_package_symlink(mod)
    except ImportError:
        ...
    return False


def check_core_package_version() -> bool:
    """Return True if core package does not need updates, based on its version.
    Return False if core package needs to be updated"""

    plugin_version = get_plugin_version()
    version = get_package_version(CORE_PACKAGE)
    logger.info(f"plugin_version {plugin_version} version {version}")

    if plugin_version != version:
        return False

    return True


def get_package_version(package):
    return sys.modules[package].__version__ if package in sys.modules else ""
    # disabled because: 2.0.4.dev0+c0c9218c != 2.0.4.dev+c0c9218c
    # try:
    #     return importlib.metadata.version(package)
    # except importlib.metadata.PackageNotFoundError:
    #     ...
    # return ""


def get_plugin_version():
    base_package = __package__.split(".")[0]
    return sys.modules[base_package].__version__


def install_packages(
    missing_packages: List[str], isolated=True, args: List[str] = None
):
    if args is None:
        args = []
    list_pip_exec = [
        PyExec(os.path.join(sysconfig.get_path("scripts"), "python3")),
        # TODO: if shutil.which works, then python3.exe is not needed
        PyExec(os.path.join(sysconfig.get_path("scripts"), "python3.exe")),
        PipExec(os.path.join(sysconfig.get_path("scripts"), "pip3")),
        PipExec(os.path.join(sysconfig.get_path("scripts"), "pip3.exe")),
        PyExec(os.path.join(QgsApplication.libexecPath(), "python")),
        # PyExec("/usr/bin/python3"),
    ]
    list_valid_pip_exec = [pip for pip in list_pip_exec if os.path.exists(pip.file())]
    if not len(list_valid_pip_exec):
        raise Exception("No available pip found")
    pip_exec = list_valid_pip_exec[0]

    args += [
        "--prefer-binary",
        "--find-links",
        Path(WHEEL_DIR).absolute().as_uri(),
    ]
    # args += ["--log", LOG_FILE]
    if isolated:
        args += ["-t", SHARED_LIB_DIR]

    pip_exec = pip_exec.with_install_args(*args)
    installed = install_packages_exec(pip_exec, missing_packages)

    for package in missing_packages:
        for package_name in REGEX_PACKAGE_NAME.findall(package):
            try:
                importlib.metadata.version(package_name)
            except Exception as e:
                logger.warning("Not able to load package after install: %s", e)

    return installed


def install_packages_exec(cmd_exec: CmdExec, package_files: List[str]):
    for _i in [1]:
        installed = False
        try:
            cmd = cmd_exec.prepare_cmd()
            if cmd:
                logger.info(cmd)
                out = subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
                )

            cmd = cmd_exec.install_cmd(package_files)
            logger.info(cmd)
            # print(cmd); cmd += " && pause || pause" # debug
            # print(cmd); cmd += "; read -n 1" # debug
            out = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            logger.info(out.stdout)
            if out.returncode == 0:
                installed = True
        except Exception as e:
            logger.exception("Unexpected error during `subprocess.run()`. %s", e)
        if installed:
            continue
        try:
            cmd = cmd_exec.prepare_cmd()
            if cmd:
                logger.info(cmd)

                out = subprocess.check_output(
                    cmd,
                    stderr=subprocess.STDOUT,
                )
                logger.info(out)

            cmd = cmd_exec.install_cmd(package_files)
            logger.info(cmd)

            out = subprocess.check_output(
                cmd,
                stderr=subprocess.STDOUT,
            )
            logger.info(out)

            installed = True
        except subprocess.CalledProcessError as e:
            logger.exception("%s: %s. %s", e.returncode, e.output, e)
        except Exception as e:
            logger.exception(e)
    return installed


def install_packages_pixi(pixi_packages: List[str]):
    # ret = os.system("echo PIXI_PROJECT_ROOT=$PIXI_PROJECT_ROOT")
    # cmd = PixiExec().with_install_args("-vvv")
    cmd = PixiExec()
    return install_packages_exec(cmd, pixi_packages)


def install_packages_conda(conda_packages: List[str]):
    cmd = CondaExec()
    return install_packages_exec(cmd, conda_packages)


def setup_lib_dir():
    os.makedirs(SHARED_LIB_DIR, exist_ok=True)
    site.addsitedir(SHARED_LIB_DIR)


def reload_module(module_name):
    """Reload module in case it is already imported"""
    importlib.invalidate_caches()
    base_module_name = module_name.split(".")[0]
    base_module = importlib.import_module(base_module_name)
    importlib.reload(base_module)
    return importlib.import_module(module_name)


class IsolatedDependencies:
    def __init__(self):
        self._modules = dict(sys.modules)
        self._paths = list(sys.path)

    @staticmethod
    def _handle_conflicting_modules(conflicting_modules: List[str]):
        modules = set(conflicting_modules)
        keys_removed = [key for key in sys.modules if key.partition(".")[0] in modules]
        for k in keys_removed:
            sys.modules.pop(k)

    @staticmethod
    def _reload_conflicting_modules(conflicting_modules: List[str]):
        modules = set(conflicting_modules)
        for module_name in modules:
            try:
                mod = importlib.import_module(module_name)
                logger.info(
                    f"Conflicting module '{module_name}' will be reloaded "
                    "from plugin shared lib"
                )
                importlib.reload(mod)
            except ImportError:
                logger.info(
                    f"Non-conflicting module '{module_name}' shall be loaded"
                    "from default QGIS lib"
                )

    def add_sys_path(self, path: Union[str, os.PathLike] = SHARED_LIB_DIR):
        # self._handle_conflicting_modules(["attr"])
        site.addsitedir(path)
        self._handle_other_plugins_sys_path_order()
        self._handle_core_package_sys_path_order()
        if Qgis.QGIS_VERSION_INT < 30000:
            # 32000 for QGIS 3.2x.
            # 33000 for QGIS 3.3x.
            pass
        else:  # QGIS 3.xx.x
            sys.path.insert(0, path)
            self._reload_conflicting_modules(["attrs"])
            sys.path.pop(0)

    @staticmethod
    def _handle_core_package_sys_path_order():
        """
        Update the import sys path, so that the core module is loaded
        in the following order:
        shared lib dir > editable symlink > default bundled site-packages path
        """
        orig_path = list(sys.path)
        try:
            mod = importlib.import_module(CORE_PACKAGE)
            if is_core_package_symlink(mod) or is_core_package_shared_lib(mod):
                return
            # move default path to end of sys.path
            default_path = os.path.dirname(mod.__path__[0])
            if default_path in sys.path:
                sys.path.remove(default_path)
            sys.path.append(default_path)

            # reload core package from different location
            importlib.reload(mod)
            path2 = os.path.dirname(mod.__path__[0])
            sys.path = list(orig_path)
            # core package in only 1 location, no need to re-order
            if path2 == default_path:
                return

            # re-order, ensure path2 is before default_path
            if path2 in sys.path:
                sys.path.remove(path2)
            idx = (
                sys.path.index(default_path)
                if default_path in sys.path
                else len(sys.path)
            )
            sys.path.insert(idx, path2)
        except ImportError:
            pass
        except Exception as e:
            logger.warning("Error when handling import order of core package: %s", e)

    def _handle_other_plugins_sys_path_order(self):
        """Make sure sys path is before sys path of other conflicting plugin"""
        other_plugins = ["XYZHubConnector"]

        other_plugins_paths = [
            p for i, p in enumerate(sys.path) for plugin in other_plugins if plugin in p
        ]
        for p in other_plugins_paths:
            sys.path.remove(p)
        sys.path.extend(other_plugins_paths)

    def unload(self):
        self.reset_sys_path()

    def reset_sys_modules(self):
        sys.modules.clear()
        sys.modules.update(self._modules)

    def reset_sys_path(self):
        sys.path.clear()
        sys.path.extend(self._paths)


def is_conda_system():
    return os.path.exists(os.path.join(sys.prefix, "conda-meta"))


def is_pixi_system():
    return bool(is_conda_system() and os.environ.get("PIXI_EXE"))


class DependencySetup:
    def __init__(self, isolated):
        self.isolated = isolated
        self.will_install_core_package = False

    @classmethod
    def from_os(cls):
        if is_conda_system():
            isolated = True
        elif platform.system() == "Darwin" or os.name == "mac":
            # mac: non-isolated dep to avoid conflict
            # in outdated bundled packages numpy, geopandas
            isolated = False
        else:
            isolated = True
        return cls(isolated=isolated)

    def install_packages(self, missing_packages: List[str]):
        args = ["--ignore-installed"] if self.will_install_core_package else []
        install_packages(missing_packages, isolated=self.isolated, args=args)

        if self.will_install_core_package:
            try:
                mod = importlib.import_module(CORE_PACKAGE)
                importlib.reload(mod)
            except Exception as e:
                logger.warning(
                    "Not able to load package '%s' after install: %s", CORE_PACKAGE, e
                )

    def should_install_deps(self, required_packages: List[str] = REQUIRED_PACKAGES):
        """Return list of packages to be installed."""
        is_core_package_location_dev_symlink = check_core_package_location()
        is_core_package_version_updated = check_core_package_version()
        will_install_core_package = (
            not is_core_package_location_dev_symlink
            and not is_core_package_version_updated
        )
        self.will_install_core_package = will_install_core_package
        logger.info(
            "is_core_package_location_dev_symlink"
            f" {is_core_package_location_dev_symlink} is_core_package_version_updated"
            f" {is_core_package_version_updated} will_install_core_package"
            f" {will_install_core_package}"
        )

        missing_packages = get_missing_packages(required_packages)
        packages = REQUIRED_PACKAGES if will_install_core_package else []
        packages += missing_packages

        return list(set(packages))
