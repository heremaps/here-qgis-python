###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.core import Qgis
from qgis.utils import iface


def show_msg_bar_warning(msg, title=None, timeout=5):
    show_msg_bar(
        msg,
        title,
        level=Qgis.MessageLevel.Warning,
        timeout=timeout,
    )


def show_msg_bar_error(msg, title=None, timeout=5):
    show_msg_bar(
        msg,
        title,
        level=Qgis.MessageLevel.Critical,
        timeout=timeout,
    )


def show_msg_bar_info(msg, title=None, timeout=5):
    show_msg_bar(
        msg,
        title,
        level=Qgis.MessageLevel.Info,
        timeout=timeout,
    )


def show_msg_bar_success(msg, title=None, timeout=5):
    show_msg_bar(
        msg,
        title,
        level=Qgis.MessageLevel.Success,
        timeout=timeout,
    )


def show_msg_bar(msg, title=None, level=Qgis.MessageLevel.NoLevel, timeout=5):
    iface.messageBar().pushMessage(
        title,
        msg,
        level=level,
        duration=timeout,
    )
