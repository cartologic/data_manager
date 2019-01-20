# -*- coding: utf-8 -*-
try:
    import ogr
except ImportError:
    from osgeo import ogr
import os
import pipes
import subprocess
import time

from cartoview.log_handler import get_logger
from geonode.geoserver.helpers import ogc_server_settings
from geonode.layers.models import Layer

from .constants import POSTGIS_OPTIONS, _downloads_dir
from .exceptions import GpkgLayerException
from .layer_manager import GpkgLayer, SourceException
from .mixins import DataManagerMixin
from .style_manager import StyleManager
from .utils import get_new_dir, get_sld_body

logger = get_logger(__name__)


class DataManager(DataManagerMixin):
    def __init__(self, package_path, is_postgis=False):
        self.path = package_path
        self.is_postgis = is_postgis
        self.get_source(is_postgis=is_postgis)

    def get_source(self, is_postgis=False):
        with self.open_source(self.path, is_postgres=is_postgis) as source:
            self.source = source
        return self.source

    def check_schema_geonode(self, layername, glayername, ignore_case=False):
        gpkg_layer = self.get_layer_by_name(layername)
        glayer = Layer.objects.get(alternate=glayername)
        if not gpkg_layer:
            raise SourceException("Cannot find this layer in Source")
        geonode_manager = DataManager(get_connection(), is_postgis=True)
        glayer = geonode_manager.get_layer_by_name(glayername.split(":").pop())
        if not glayer:
            raise GpkgLayerException(
                "Layer {} Cannot be found in Source".format(glayername))
        check = DataManager.compare_schema(gpkg_layer, glayer, ignore_case)
        return check

    def layer_exists(self, layername):
        return DataManager.source_layer_exists(self.source, layername)

    def get_layers(self):
        return self.get_source_layers(self.source)

    def get_layernames(self):
        return tuple(layer.name for layer in self.get_layers())

    def get_layer_by_name(self, layername):
        if self.layer_exists(layername):
            return GpkgLayer(
                self.source.GetLayerByName(layername), self.source)
        return None

    def read_schema(self):
        return self.read_source_schema(self.source)

    def get_features(self):
        return self.get_layers_features(self.get_layers())

    def _cmd_lyr_postgis(self,
                         gpkg_path,
                         connectionString,
                         layername,
                         options=POSTGIS_OPTIONS._asdict()):

        overwrite = options.get('overwrite', POSTGIS_OPTIONS.overwrite)
        skipfailures = options.get('skipfailures',
                                   POSTGIS_OPTIONS.skipfailures)
        append_layer = options.get('append', POSTGIS_OPTIONS.append)
        update_layer = options.get('update', POSTGIS_OPTIONS.update)
        command = """ogr2ogr {} {} {} -f "PostgreSQL" PG:"{}" {} {}  {} """\
            .format("-overwrite" if overwrite else "",
                    "-update" if update_layer else "",
                    "-append" if append_layer else "",
                    connectionString,
                    gpkg_path, "-skipfailures" if skipfailures else "",
                    pipes.quote(layername))
        return command

    def execute(self, cmd):
        p = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        return out, err

    def layer_to_postgis(self,
                         layername,
                         connectionString,
                         overwrite=True,
                         temporary=False,
                         launder=False,
                         name=None):
        with self.open_source(connectionString, is_postgres=True) as source:
            layer = self.source.GetLayerByName(layername)
            assert layer
            layer = GpkgLayer(layer, source)
            return layer.copy_to_source(
                source,
                overwrite=overwrite,
                temporary=temporary,
                launder=launder,
                name=name)

    def layer_to_postgis_cmd(self, layername, connectionString, options=None):
        cmd = self._cmd_lyr_postgis(
            self.path,
            connectionString,
            layername,
            options=options if options else POSTGIS_OPTIONS._asdict())
        out, err = self.execute(cmd)
        if not err:
            logger.warning("{} Added Successfully".format(layername))

    @staticmethod
    def postgis_as_gpkg(connectionString, dest_path, layernames=None):
        if not dest_path.endswith(".gpkg"):
            dest_path += ".gpkg"
        with DataManager.open_source(connectionString, is_postgres=True) as postgis_source:
            ds = ogr.GetDriverByName('GPKG').CreateDataSource(dest_path)
            layers = DataManager.get_source_layers(postgis_source) \
                if not layernames \
                else [layer for layer in
                      DataManager.get_source_layers(postgis_source)
                      if layer and layer.name in layernames]
            for lyr in layers:
                ds.CopyLayer(lyr.gpkg_layer, lyr.name)
        return dest_path

    @staticmethod
    def backup_portal(dest_path=None):
        final_path = None
        if not dest_path:
            dest_path = get_new_dir(base_dir=_downloads_dir)
        file_suff = time.strftime("%Y_%m_%d-%H_%M_%S")
        package_dir = os.path.join(dest_path, "backup_%s.gpkg" % (file_suff))
        connection_string = get_connection()
        try:
            if not os.path.isdir(dest_path) or not os.access(
                    dest_path, os.W_OK):
                raise Exception(
                    'maybe destination is not writable or not a directory')
            with DataManager.open_source(connection_string, is_postgres=True) as ds:
                if ds:
                    all_layers = Layer.objects.all()
                    layer_styles = []
                    table_names = []
                    for layer in all_layers:
                        typename = str(layer.alternate)
                        table_name = typename.split(":").pop()
                        if DataManager.source_layer_exists(ds, table_name):
                            table_names.append(table_name)
                            gattr = str(
                                layer.attribute_set.filter(
                                    attribute_type__contains='gml').first()
                                .attribute)
                            layer_style = layer.default_style
                            sld_url = layer_style.sld_url
                            style_name = str(layer_style.name)
                            layer_styles.append((table_name, gattr, style_name,
                                                 get_sld_body(sld_url)))
                    DataManager.postgis_as_gpkg(
                        connection_string, package_dir, layernames=table_names)
                    stm = StyleManager(package_dir)
                    stm.create_table()
                    for style in layer_styles:
                        stm.add_style(*style, default=True)
            final_path = dest_path

        except Exception as e:
            logger.error(e.message)
        finally:
            return final_path


def get_connection():
    db_settings = ogc_server_settings.datastore_db
    db_name = db_settings.get('NAME')
    user = db_settings.get('USER')
    password = db_settings.get('PASSWORD')
    host = db_settings.get('HOST', 'localhost')
    port = db_settings.get('PORT', 5432)
    return DataManager.build_connection_string(host, db_name, user, password,
                                               int(port) if port else 5432)


def get_store_connection(storename, workspace=None):
    from geonode.geoserver.helpers import (get_store, gs_catalog)
    from django.conf import settings
    if not workspace:
        workspace = settings.DEFAULT_WORKSPACE
    store = get_store(gs_catalog, storename, workspace)
    db = ogc_server_settings.datastore_db
    db_name = store.connection_parameters.get('database')
    user = db['USER']
    password = db['PASSWORD']
    host = store.connection_parameters['host']
    port = store.connection_parameters['port']
    return DataManager.build_connection_string(host, db_name, user, password,
                                               int(port) if port else 5432)
