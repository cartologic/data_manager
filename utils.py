# -*- coding: utf-8 -*-
import requests
from django.conf import settings
from geonode.geoserver.helpers import (get_store, gs_catalog,
                                       ogc_server_settings)
from requests.auth import HTTPBasicAuth
from slugify import Slugify

DEFAULT_WORKSPACE = settings.DEFAULT_WORKSPACE

SLUGIFIER = Slugify(separator='_')


def get_sld_body(url):
    req = requests.get(
        url,
        auth=HTTPBasicAuth(ogc_server_settings.credentials[0],
                           ogc_server_settings.credentials[1]))
    return req.text


def get_gs_store(storename=ogc_server_settings.datastore_db['NAME'],
                 workspace=DEFAULT_WORKSPACE):
    return get_store(gs_catalog, storename, workspace)
