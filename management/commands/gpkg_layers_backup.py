# -*- coding: utf-8 -*-
from __future__ import print_function

import multiprocessing
import os
import sys
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from geonode.layers.models import Layer

from data_manager.handlers import DataManager, get_connection
from data_manager.style_manager import StyleManager
from data_manager.utils import get_sld_body

backup_process = None


class Command(BaseCommand):
    help = 'Backup portal layers as geopackage'

    def add_arguments(self, parser):
        parser.add_argument(
            '-d',
            '--destination',
            dest='destination',
            default=settings.BASE_DIR,
            help='Location to save geopackage')

    def handle(self, *args, **options):
        global backup_process
        dest_dir = options.get('destination')
        try:
            package_dir = None

            def progress():
                global package_dir
                package_dir = DataManager.backup_portal(dest_path=dest_dir)

            backup_process = multiprocessing.Process(target=progress)
            backup_process.start()
            i = 0
            while backup_process.is_alive():
                time.sleep(1)
                sys.stdout.write(
                    "\r%s" % ("[" + ("=" * i) + ">]" + "Backup In Progress"))
                sys.stdout.flush()
                i += 1
            print(
                '\n****************** Backup Created ****************** \n%s\n'
                % (package_dir))
        except Exception as e:
            if backup_process and backup_process.is_alive():
                backup_process.terminate()
            print("\nFailed due to %s" % (e))
            print('\n====== Backup Operation Failed :( ======')
