from django.core.management.base import BaseCommand
from django.conf import settings
from gpkg_manager.handlers import GpkgManager
from geonode.layers.models import Layer
from geonode.geoserver.helpers import (
    gs_catalog, get_store, ogc_server_settings)
import os
import time


class Command(BaseCommand):
    help = 'Backup portal layers as geopackage'

    def add_arguments(self, parser):
        parser.add_argument(
            '-d',
            '--destination',
            dest='destination',
            default=settings.BASE_DIR,
            help='Location to save geopackage'
        )

    def handle(self, *args, **options):
        dest_dir = options.get('destination')
        file_suff = time.strftime("%Y_%m_%d-%H_%M_%S")
        package_dir = os.path.join(dest_dir, "backup_%s.gpkg" % (file_suff))

        storename = ogc_server_settings.datastore_db['NAME']
        store = get_store(
            gs_catalog, storename, settings.DEFAULT_WORKSPACE)
        db = ogc_server_settings.datastore_db
        db_name = store.connection_parameters['database']
        user = db['USER']
        password = db['PASSWORD']
        host = store.connection_parameters['host']
        port = store.connection_parameters['port']
        connection_string = GpkgManager.build_connection_string(
            host, db_name, user, password, int(port) if port else 5432)
        ds = GpkgManager.open_source(connection_string, is_postgres=True)
        if ds:
            geonode_layers = [str(layer.split(":").pop(
            )) for layer in Layer.objects.values_list('typename', flat=True)]
            geonode_layers = [
                lyr for lyr in geonode_layers
                if GpkgManager.source_layer_exists(ds, lyr)]
            GpkgManager.postgis_as_gpkg(connection_string, package_dir)
            print('Backup Created ======> %s' % (package_dir))
