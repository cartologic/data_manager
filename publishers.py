from requests.auth import HTTPBasicAuth
from geonode.geoserver.helpers import ogc_server_settings
import requests
from django.conf import settings

DEFAULT_WORKSPACE = settings.DEFAULT_WORKSPACE


class GeoserverPublisher(object):
    def __init__(self, geoserver_url=ogc_server_settings.LOCATION,
                 workspace=DEFAULT_WORKSPACE,
                 datastore=ogc_server_settings.datastore_db['NAME'],
                 geoserver_user={'username': ogc_server_settings.credentials[0],
                                 'password': ogc_server_settings.credentials[1]}):
        self.base_url = geoserver_url
        self.workspace = workspace
        self.datastore = datastore
        self.username = geoserver_user.get(
            'username', ogc_server_settings.credentials[0])
        self.password = geoserver_user.get(
            'password', ogc_server_settings.credentials[1])

    @property
    def featureTypes_url(self):
        return "{}rest/workspaces/{}/datastores/{}/featuretypes"\
            .format(self.base_url, self.workspace, self.datastore)

    def publish_postgis_layer(self, layername):
        if layername:
            req = requests.post(self.featureTypes_url,
                                headers={'Content-Type': "application/json"},
                                auth=HTTPBasicAuth(
                                    self.username, self.password),
                                json={"featureType": {"name": layername,
                                                      "nativeName": layername}
                                      })
            if req.status_code == 200:
                return True
        return False

# TODO: GeonodePublisher
