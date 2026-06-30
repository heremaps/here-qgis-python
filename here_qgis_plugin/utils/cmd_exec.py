###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os
import shutil
from abc import abstractmethod
from typing import List


def quoted_string(text: str):
    return f'"{text}"'


class CmdExec:
    @abstractmethod
    def prepare_cmd(self) -> List[str]:
        raise NotImplementedError()

    @abstractmethod
    def install_cmd(self, package_files: List[str]) -> List[str]:
        raise NotImplementedError()

    @abstractmethod
    def with_install_args(self, *install_args: str) -> "CmdExec":
        raise NotImplementedError()

    @abstractmethod
    def file(self) -> str:
        raise NotImplementedError()

    def prepare_cmd_str(self):
        return " ".join([quoted_string(s) for s in self.prepare_cmd()])

    def install_cmd_str(self, package_files: List[str]):
        return " ".join([quoted_string(s) for s in self.install_cmd(package_files)])


class PipExec(CmdExec):
    def __init__(self, pip_exec, *install_args: str):
        self.pip_exec = pip_exec
        self.install_args = list(install_args)

    def with_install_args(self, *install_args: str):
        return PipExec(self.pip_exec, *install_args)

    def file(self) -> str:
        return shutil.which(self.pip_exec) or self.pip_exec

    def prepare_cmd(self) -> List[str]:
        return []

    def install_cmd(self, package_files: List[str]) -> List[str]:
        return [self.pip_exec, "install"] + self.install_args + package_files


class PyExec(CmdExec):
    def __init__(self, py_exec, *install_args: str):
        self.py_exec = py_exec
        self.install_args = list(install_args)

    def with_install_args(self, *install_args: str):
        return PyExec(self.py_exec, *install_args)

    def file(self) -> str:
        return shutil.which(self.py_exec) or self.py_exec

    def prepare_cmd(self) -> List[str]:
        return [self.py_exec, "-m", "ensurepip"]

    def install_cmd(self, package_files: List[str]) -> List[str]:
        return (
            [self.py_exec, "-m", "pip", "install"] + self.install_args + package_files
        )


class PixiExec(CmdExec):
    def __init__(self, *install_args: str):
        pixi_exec = os.environ.get("PIXI_EXE")
        if not os.path.exists(pixi_exec):
            raise RuntimeError("Pixi executable not found: %s" % pixi_exec)
        self.pixi_exec = pixi_exec
        self.install_args = list(install_args)

    def with_install_args(self, *install_args: str):
        return PixiExec(*install_args)

    def file(self) -> str:
        return self.pixi_exec

    def prepare_cmd(self) -> List[str]:
        return []

    def install_cmd(self, package_files: List[str]) -> List[str]:
        return [self.pixi_exec, "add"] + self.install_args + package_files


class CondaExec(CmdExec):
    def __init__(self, *install_args: str):
        self.conda_exec = "conda"
        self.install_args = list(install_args)

    def with_install_args(self, *install_args: str):
        return CondaExec(*install_args)

    def file(self) -> str:
        return shutil.which(self.conda_exec) or self.conda_exec

    def prepare_cmd(self) -> List[str]:
        return []

    def install_cmd(self, package_files: List[str]) -> List[str]:
        return [self.conda_exec, "install"] + self.install_args + package_files
