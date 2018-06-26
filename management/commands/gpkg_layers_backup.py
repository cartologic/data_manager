# -*- coding: utf-8 -*-
from __future__ import print_function
from django.core.management.base import BaseCommand
from django.conf import settings
from gpkg_manager.handlers import GpkgManager, StyleManager
from geonode.layers.models import Layer
import os
import time
import sys
import multiprocessing
from gpkg_manager.utils import get_connection, get_sld_body
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
                all_layers = Layer.objects.all()
                layer_styles = []
                table_names = []
                for layer in all_layers:
                    # TODO: check if it alternate  or typename :D
                    typename = str(layer.alternate)
                    table_name = typename.split(":").pop()
                    if GpkgManager.source_layer_exists(ds, table_name):
                        table_names.append(table_name)
                        gattr = str(layer.attribute_set.filter(
                            attribute_type__contains='gml').first().attribute)
                        layer_style = layer.default_style
                        sld_url = layer_style.sld_url
                        style_name = str(layer_style.name)
                        layer_styles.append(
                            (table_name, gattr, style_name,
                             get_sld_body(sld_url)))

                def progress():
                    global running
                    GpkgManager.postgis_as_gpkg(
                        connection_string, package_dir, layernames=table_names)
                    stm = StyleManager(package_dir)
                    stm.create_table()
                    for style in layer_styles:
                        stm.add_style(*style, default=True)
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
