###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


def get_features_ids(features, first_id_col=None, second_id_col=None):
    features_ids = []
    for f in features:
        if second_id_col is None:
            # No "xyz_id" column - layer from v2
            features_ids.append(f[first_id_col])
        elif isinstance(f[first_id_col], str):
            # "id" column is present, and feature has this field,
            # means that this feature was loaded by v2
            features_ids.append(f[first_id_col])
        else:
            # f[first_id_col] is None, means feature was loaded by v1
            features_ids.append(f[second_id_col])
    return features_ids


def trim_filename(is_v1_layer: bool, is_reloaded: bool, filename: str):
    if is_v1_layer and not is_reloaded:
        filename_end = filename.find("|")
        filename = filename[:filename_end]
    return filename
