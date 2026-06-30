###############################################################################
#
# Copyright (c) 2025 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import json
from typing import cast

import mom_core.mom.core.component.linear_range.base.linear_range as LinearRange  # noqa
import mom_core.mom.core.feature.feature_collection.base.feature_collection as MomFeatureCollection  # noqa
import mom_core.mom.core.feature.road_segment.base.road_segment as RoadSegment
import mom_core.schema.geometry.v3.base.geometry_v_3 as Geometry
import mom_core_geojson.Shift as Shift
from geojson import FeatureCollection


def osm_way_to_mom_topology(way: dict) -> RoadSegment.RoadSegment:
    tags = way["tags"]
    mom_topology = RoadSegment.RoadSegment(
        id=str(way["id"]),
        geometry=Geometry.LineString(
            [
                Geometry.Point(
                    longitude=float(geom["lon"]),
                    latitude=float(geom["lat"]),
                    elevation=0.0,
                )
                for geom in way["geometry"]
            ]
        ),
        bbox=None,
        non_spatial_partition_key=None,
        reference_point=None,
        properties=RoadSegment.RoadSegmentProperties(
            speed_limit=[
                RoadSegment.SpeedLimitRange(
                    value_kph=(
                        int(tags["maxspeed"])
                        if "maxspeed" in tags and tags["maxspeed"] != "none"
                        else None
                    ),
                    is_unlimited=False,
                    applies_to=RoadSegment.RoadSegmentDirection0.UNDEFINED,
                    source=RoadSegment.SpeedLimitSource.UNDEFINED,
                    range=LinearRange.LinearRange(1.0, 0.0),
                )
            ],
            surface_type=[
                RoadSegment.SurfaceTypeRange(
                    range=LinearRange.LinearRange(1.0, 0.0),
                    value=RoadSegment.SURFACE_TYPE_VALUES.get(
                        tags["surface"].upper() if "surface" in tags else "",
                        RoadSegment.SurfaceType.UNDEFINED,
                    ),
                    applies_to=RoadSegment.RoadSegmentDirection0.UNDEFINED,
                ),
            ],
            meta=None,
            intersection_category=[],
            start_connector=None,
            end_connector=None,
            iso_cc=[],
            functional_class=[],
            access_characteristics=[],
            divider=[],
            low_mobility=[],
            built_up_area_road=[],
            grade_category=[],
            over_under_pass_indicator=[],
            truck_road_type=[],
            category=[],
            speed_category=[],
            average_speed=[],
            pedestrian_preferred=[],
            is_in_process_data=[],
            traffic_location_references=set(),
            right_of_way_regulation=[],
            priority=set(),
            road_class=[],
            address_ranges=[],
            conditional_attribute_ranges=[],
            conditional_attribute_points=[],
            road_segment_characteristics=None,
        ),
    )

    return mom_topology


def osm_features_to_mom_feature_collection_dict(ways) -> FeatureCollection:
    features = []
    for way in ways:
        features.append(osm_way_to_mom_topology(way))
    mom_feat_coll = MomFeatureCollection.MomFeatureCollection(features)
    return cast(FeatureCollection, json.loads(Shift.to_target(mom_feat_coll)))
