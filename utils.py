# -*- coding: utf-8 -*-
import os
import time
from uuid import uuid4

import requests
from django.conf import settings
from geonode.geoserver.helpers import (get_store, gs_catalog,
                                       ogc_server_settings)
from requests.auth import HTTPBasicAuth
from slugify import Slugify

from cartoview.app_manager.helpers import create_direcotry

from .constants import _temp_dir

DEFAULT_WORKSPACE = settings.DEFAULT_WORKSPACE

SLUGIFIER = Slugify(separator='_')


def get_new_dir(base_dir=_temp_dir):
    rand_str = uuid4().__str__().replace('-', '')[:8]
    timestr = time.strftime("%Y/%m/%d/%H/%M/%S")
    target = os.path.join(base_dir, timestr, rand_str)
    create_direcotry(target)
    return target


def get_sld_body(url):
    req = requests.get(
        url,
        auth=HTTPBasicAuth(ogc_server_settings.credentials[0],
                           ogc_server_settings.credentials[1]))
    return req.text


def get_gs_store(storename=None,
                 workspace=DEFAULT_WORKSPACE):
    if not storename:
        storename = ogc_server_settings.datastore_db.get('NAME', None)
    return get_store(gs_catalog, storename, workspace)


def get_store_schema(storename=ogc_server_settings.datastore_db['NAME']):
    store = get_store(gs_catalog, storename, settings.DEFAULT_WORKSPACE)
    return store.connection_parameters.get('schema', 'public')
