###############################################################################
#
# Copyright (c) 2026 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


def print_version():
    from .. import __version__

    print("here_qgis_plugin", __version__)

    from qgis.PyQt import QtCore

    print(QtCore, QtCore.__file__)
    print("Qt compile", QtCore.QT_VERSION_STR)
    print("Qt runtime", QtCore.qVersion())
    print("PyQt", QtCore.PYQT_VERSION_STR)

    import qgis

    # debug AttributeError: module 'qgis' has no attribute 'core'
    print(qgis, qgis.__file__, dir(qgis))

    from qgis._core import Qgis
    from qgis.core import Qgis as Qgis2

    print(qgis._core, qgis._core.__file__)
    print(Qgis, Qgis2)

    print(
        "Qgis",
        Qgis.QGIS_VERSION,
        Qgis.QGIS_VERSION_INT,
        "commit",
        Qgis.QGIS_DEV_VERSION,
    )


if __name__ == "__main__":
    try:
        print_version()
    except Exception:
        import traceback

        traceback.print_exc()
