###############################################################################
#
# Copyright (c) 2026 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


__author__ = "HERE Europe B.V."
__email__ = "here_qgis_plugin_dev_team@here.com"
__version__ = "2.0.16"
__copyright__ = "Copyright (c) 2026 HERE Europe B.V."


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load HereQgisPlugin class

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """

    from . import config
    from .utils.dependencies import (
        IsolatedDependencies,
        install_packages_with_confirm_dialog,
    )
    from .utils.logging import get_logger, setup_logger

    setup_logger()

    logger = get_logger(__name__)
    logger.info("init plugin " + __name__)
    logger.info("logging to file: " + config.LOG_FILE)

    init_resources_rc(logger)

    deps = IsolatedDependencies()
    deps.add_sys_path()
    ok = install_packages_with_confirm_dialog()
    if not ok:
        from .plugin_without_dependencies import PluginWithoutDependencies

        return PluginWithoutDependencies(iface)

    else:
        from .here_qgis_plugin import HereQgisPlugin

        return HereQgisPlugin(iface, deps)


def init_resources_rc(logger):
    # Initialize Qt resources from generated resources_rc.py

    # Initialize Qt resources from file ui/resources.py
    try:
        from .ui import resources

    except ImportError as e:
        logger.warning(repr(e))
