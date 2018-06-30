from django.conf import settings
from geonode.geoserver.helpers import (
    gs_catalog, get_store, ogc_server_settings)
import requests
from requests.auth import HTTPBasicAuth
DEFAULT_WORKSPACE = settings.DEFAULT_WORKSPACE


def get_sld_body(url):
    req = requests.get(url,
                       auth=HTTPBasicAuth(
                           ogc_server_settings.credentials[0],
                           ogc_server_settings.credentials[1]))
    return req.text


def get_gs_store(storename=ogc_server_settings.datastore_db['NAME'],
                 workspace=DEFAULT_WORKSPACE):
    return get_store(
        gs_catalog, storename, workspace)
