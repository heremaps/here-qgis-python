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

import mom_internal.mom.internal.component.linear_range.base.linear_range as LinearRange  # noqa
import mom_internal.mom.internal.enumeration.feature_type.base.feature_type as FeatureType  # noqa
import mom_internal.mom.internal.feature.feature_collection.base.feature_collection as MomFeatureCollection  # noqa
import mom_internal.mom.internal.feature.topology.base.topology as Topology
import mom_internal.schema.geometry.v3.base.geometry_v_3 as Geometry
import mom_internal_geojson.Shift as Shift
from geojson import FeatureCollection


def osm_way_to_mom_topology(way: dict) -> Topology.Topology:
    tags = way["tags"]
    mom_topology = Topology.Topology(
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
        properties=Topology.TopologyProperties(
            feature_type=FeatureType.FeatureType.TOPOLOGY,
            speed_limit=[
                Topology.SpeedLimitRange(
                    value_kph=(
                        int(tags["maxspeed"])
                        if "maxspeed" in tags and tags["maxspeed"] != "none"
                        else None
                    ),
                    is_unlimited=False,
                    applies_to=Topology.TopologyDirection.UNDEFINED,
                    source=Topology.SpeedLimitSource.UNDEFINED,
                    range=LinearRange.LinearRange(1.0, 0.0),
                    confidence=None,
                )
            ],
            surface_type=[
                Topology.SurfaceTypeRange(
                    range=LinearRange.LinearRange(1.0, 0.0),
                    value=Topology.SURFACE_TYPE_VALUES.get(
                        tags["surface"].upper() if "surface" in tags else "",
                        Topology.SurfaceType.UNDEFINED,
                    ),
                    confidence=None,
                    applies_to=Topology.TopologyDirection.UNDEFINED,
                ),
            ],
            meta=None,
            external_ids=set(),
            mapcreator=None,
            rmob=None,
            ground_truth=None,
            extension_osm=None,
            xyz=None,
            iso_country_code=None,
            confidence=None,
            branch=None,
            z_level=[],
            adas_topology=None,
            intersection_category=[],
            start_node_id="",
            end_node_id="",
            iso_cc=[],
            functional_class=[],
            roads=[],
            access_characteristics=[],
            divider=[],
            low_mobility=[],
            built_up_area_road=[],
            grade_category=[],
            over_under_pass_indicator=[],
            conditional_attributes=[],
            truck_road_type=[],
            category=[],
            speed_category=[],
            infrastructure_separation=[],
            topology_characteristics=None,
            average_speed=[],
            pedestrian_preferred=[],
            is_in_process_data=[],
            link_accuracy=[],
            traffic_location_references=set(),
            right_of_way_regulation=[],
            priority=set(),
            road_class=[],
            start_node_publication_id=None,
            external_references=[],
            end_node_publication_id=None,
            super_elevation_class=[],
            temporary_speed_limit=set(),
            aligned_points=[],
            publication_data=None,
            low_speed_zone=[],
            non_default_traffic_sense=[],
            median=[],
            rds_tmc_codes=[],
            gnss_reliability=[],
            offroad_flags=None,
            raised_surface_area=[],
            bicycle=[],
            coverage_indicator=[],
            expanded_inclusion=[],
            traffic_intrusion_risks=[],
        ),
    )

    return mom_topology


def osm_features_to_mom_feature_collection_dict(ways) -> FeatureCollection:
    features = []
    for way in ways:
        features.append(osm_way_to_mom_topology(way))
    mom_feat_coll = MomFeatureCollection.MomFeatureCollection(features)
    return cast(FeatureCollection, json.loads(Shift.to_target(mom_feat_coll)))
