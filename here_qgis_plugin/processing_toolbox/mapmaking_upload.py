###############################################################################
#
# Copyright (c) 2023 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


from qgis.core import (
    QgsProcessing,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorLayer,
    QgsProject,
)

from here_qgis.api.here_utils import get_id_from_hrn
from here_qgis.api.mapmaking import MapMakingAPI
from here_qgis.helper_functions import get_mom_geojson_from_geojson

from ..api_factory import create_api_for_processing
from ..flatten.qgis_to_geojson import QgisFeaturesToGeoJSON
from ..settings import get_path, get_project_hrn
from .get_and_load import DEFAULT_IML_LAYERS
from .here_processing_base import HereProcessingAlgorithm, HereProcessingException


class MapMakingUpload(HereProcessingAlgorithm):
    @classmethod
    def createInstance(cls):
        return cls()

    def displayName(self) -> str:
        return "MM: MapMaking Upload"

    def __init__(self):
        super().__init__()
        self.iml_layers = DEFAULT_IML_LAYERS
        self.map_types = ["input", "livemap"]

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # HERE credentials
        self.addParameter(
            QgsProcessingParameterFile(
                "HERE_CREDENTIALS_FILE",
                "Specify HERE credentials file",
                behavior=QgsProcessingParameterFile.Behavior.File,
                fileFilter="All Files (*.*)",
                defaultValue=get_path(),
                optional=True,
            )
        )

        # vector layer to upload
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "upload_layer",
                "Layer to upload",
                types=[QgsProcessing.SourceType.TypeVectorAnyGeometry],
                optional=True,
                defaultValue=None,
            )
        )

        # project hrn
        self.addParameter(
            QgsProcessingParameterString(
                "project_hrn",
                "Specify Project HRN",
                multiLine=False,
                defaultValue=get_project_hrn(),
                optional=True,
            )
        )

        # self.addParameter(
        #     QgsProcessingParameterEnum(
        #         "layer_id",
        #         "Catalog layer",
        #         options=self.iml_layers,
        #         allowMultiple=False,
        #         usesStaticStrings=False,
        #         defaultValue=0,
        #     )
        # )

        self.addParameter(
            QgsProcessingParameterString(
                "layer_id",
                "Catalog layer ID (e.g., topology, building, or custom)",
                optional=False,
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                "map_type",
                "Map to upload",
                options=self.map_types,
                allowMultiple=False,
                usesStaticStrings=True,
                defaultValue="input",
            )
        )

        # Upload selected features only
        self.addParameter(
            QgsProcessingParameterBoolean(
                "upload_selected_only",
                "Upload selected features only",
                defaultValue=False,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                "upload_edited",
                "Upload edited features",
                defaultValue=False,
                optional=True,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        HERE is where the processing itself takes place.
        """
        upload_edited = self.parameterAsBoolean(parameters, "upload_edited", context)
        # Project ID where data should be uploaded
        project_hrn = parameters.get("project_hrn", "")
        if not project_hrn or len(project_hrn.split("/")) < 2:
            raise HereProcessingException("Invalid project HRN provided.")
        project_id = get_id_from_hrn(project_hrn)

        here_cred_path = parameters.get("HERE_CREDENTIALS_FILE", "")
        map_making = create_api_for_processing(
            MapMakingAPI, here_cred_path, project_hrn=parameters["project_hrn"]
        )

        map_making_response = map_making.fetch_catalogs(project_id)
        # upload data if any
        output = {"Project ID": project_id}
        if parameters["upload_layer"]:
            # Layer that the data needs to be uploaded into
            layer_id = parameters["layer_id"]
            # Get the provider
            layer_upload = parameters["upload_layer"]
            layer_upload = QgsProject.instance().mapLayer(layer_upload)

            # Upload only selected features if checkbox is enabled
            upload_selected_only = parameters["upload_selected_only"]
            qgis_2_geo = QgisFeaturesToGeoJSON(
                layer_upload.selectedFeatures()
                if upload_selected_only
                else list(layer_upload.getFeatures())
            )
            upload_data = qgis_2_geo.list_of_qgis_features_2_feature_coll()

            mom_geojson, is_valid_mom = get_mom_geojson_from_geojson(upload_data)

            if upload_edited:
                response = map_making.upload_edited_data(
                    mom_geojson,
                    map_making_response.get_catalogs()[parameters["map_type"]],
                    layer_id,
                )
            else:
                response = map_making.upload_data(
                    mom_geojson,
                    map_making_response.get_catalogs()[parameters["map_type"]],
                    layer_id,
                )

            output["feature_count"] = len(response["features"])
            output["layer_id"] = layer_id
            output["catalog"] = parameters["map_type"]
            output["is_valid_mom"] = is_valid_mom
            feedback.pushInfo("{} features uploaded".format(output["feature_count"]))
            output["message"] = "{} features uploaded".format(output["feature_count"])
            output["success"] = True

        return output
