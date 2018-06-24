# -*- coding: utf-8 -*-
from __future__ import print_function
from django.core.management.base import BaseCommand
from django.conf import settings
from gpkg_manager.handlers import GpkgManager
from geonode.layers.models import Layer
from geonode.geoserver.helpers import (
    gs_catalog, get_store, ogc_server_settings)
import os
import time
import sys
import multiprocessing
from gpkg_manager.utils import get_connection
backup_process = None


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
        global backup_process
        dest_dir = options.get('destination')
        file_suff = time.strftime("%Y_%m_%d-%H_%M_%S")
        package_dir = os.path.join(dest_dir, "backup_%s.gpkg" % (file_suff))
        connection_string = get_connection()
        try:
            if not os.path.isdir(dest_dir) or not os.access(dest_dir, os.W_OK):
                raise Exception(
                    'maybe destination is not writable or not a directory')
            ds = GpkgManager.open_source(connection_string, is_postgres=True)
            if ds:
                geonode_layers = [str(layer.split(":").pop(
                )) for layer in Layer.objects.values_list('typename',
                                                          flat=True)]
                geonode_layers = [lyr for lyr in geonode_layers
                                  if GpkgManager.source_layer_exists(ds, lyr)]

                def progress():
                    global running
                    GpkgManager.postgis_as_gpkg(connection_string, package_dir)
                backup_process = multiprocessing.Process(target=progress)
                backup_process.start()
                i = 0
                while backup_process.is_alive():
                    time.sleep(1)
                    sys.stdout.write("\r%s" %
                                     ("["+("="*i)+">]"+"Backup In Progress"))
                    sys.stdout.flush()
                    i += 1
                print('\n****************** Backup Created ****************** \n%s\n' %
                      (package_dir))
        except Exception as e:
            if backup_process and backup_process.is_alive():
                backup_process.terminate()
            print("\nFailed due to %s" % (e.message))
            print('\n====== Backup Operation Failed :( ======')
