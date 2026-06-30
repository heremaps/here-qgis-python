#!/bin/env python
###############################################################################
#
# Copyright (c) 2024 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

# flake8: noqa

############################################################################
##################  usage & settings #######################################
############################################################################

# 1. Modfiy below jsonMomDataFilePath to YOUR_INPUT_MOM_JSON_FILE
#    e.g. file downloaded from https://platform.here.com/data/hrn:here:data::org-realm-id:catalog-id/overview

#    !!!!! by using unix conform slashes --> '/' !!!!!!!!!!!!
jsonMomDataFilePath = "c:/yourData/jsonMomData"

# 2. Modfiy below inputJsonFile with YOUR_INPUT_MOM_JSON_FILE
inputJsonFile = "topology_v10564_tile_23600771.json"

# 3. Modfiy below outputJsonFile with YOUR_OUTPUT_MOM_JSON_FILE
outputJsonFile = "topology_v10564_tile_23600771_transformed.json"


# 4. execute script by click on the green execution button

# 5. Import the new generated transformed outputJsonFile via
#    QGIS [Layer]-->[Add Layer]-->[Add Vector Layer] into QGIS


############################################################################
##################  END usage & settings ##################################
############################################################################


import json

input1 = jsonMomDataFilePath + "/" + inputJsonFile
output1 = jsonMomDataFilePath + "/" + outputJsonFile


def transform_props(props):
    """Convert types to string, because QgsField cannot handle"""
    return {
        k: (
            json.dumps(v, ensure_ascii=False)
            if isinstance(v, (dict, list, tuple))
            else v
        )
        for k, v in props.items()
    }


def transform_feat(feat):
    return {k: transform_props(v) if k == "properties" else v for k, v in feat.items()}


def transform(obj):
    return {
        k: [transform_feat(ft) for ft in v] if k == "features" else v
        for k, v in obj.items()
    }


print("")
print("input file:   " + input1)
print("")
print("outout file:   " + output1)


def do_transform(input1, output1):
    with open(input1) as f:
        obj = json.load(f)
    with open(output1, "w") as f:
        json.dump(transform(obj), f, ensure_ascii=False)


do_transform(input1, output1)
