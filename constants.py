# -*- coding: utf-8 -*-
import os
from collections import namedtuple

from cartoview.app_manager.helpers import create_direcotry

LayerPostgisOptions = namedtuple(
    'LayerPostgisOptions', ['skipfailures', 'overwrite', 'append', 'update'])
POSTGIS_OPTIONS = LayerPostgisOptions(True, True, False, False)

_temp_dir = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'tmp_generator')
_downloads_dir = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'downloads')
create_direcotry(_temp_dir)
create_direcotry(_downloads_dir)
