###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


def get_id_from_hrn(hrn: str):
    """
    Get id from hrn (project hrn, catalog hrn, etc.)

    Args:
        hrn:

    Returns: id

    """
    return hrn.split("/")[-1]
