from geonode.geoserver.helpers import (
    gs_catalog, get_store, ogc_server_settings)
from django.conf import settings
from .handlers import GpkgManager


def get_connection():
    storename = ogc_server_settings.datastore_db['NAME']
    store = get_store(
        gs_catalog, storename, settings.DEFAULT_WORKSPACE)
    db = ogc_server_settings.datastore_db
    db_name = store.connection_parameters['database']
    user = db['USER']
    password = db['PASSWORD']
    host = store.connection_parameters['host']
    port = store.connection_parameters['port']
    return GpkgManager.build_connection_string(
        host, db_name, user, password, int(port) if port else 5432)
