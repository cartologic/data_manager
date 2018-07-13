# -*- coding: utf-8 -*-
try:
    import ogr
except:
    from osgeo import ogr
import pipes
import subprocess

from django.conf import settings
from geonode.geoserver.helpers import (get_store, gs_catalog,
                                       ogc_server_settings)
from geonode.layers.models import Layer

from cartoview.log_handler import get_logger

from .constants import POSTGIS_OPTIONS
from .layer_manager import GpkgLayer, SourceException

logger = get_logger(__name__)


class GpkgManager(object):
    def __init__(self, package_path, is_postgis=False):
        self.path = package_path
        self.get_source(is_postgis=is_postgis)

    @staticmethod
    def build_connection_string(DB_server,
                                DB_Name,
                                DB_user,
                                DB_Pass,
                                DB_Port=5432):
        connectionString = "host=%s port=%d dbname=%s user=%s password=%s" % (
            DB_server, DB_Port, DB_Name, DB_user, DB_Pass)
        return connectionString

    @staticmethod
    def open_source(source_path, is_postgres=False):
        full_path = "PG: " + source_path if is_postgres else source_path
        return ogr.Open(full_path)

    def get_source(self, is_postgis=False):
        self.source = self.open_source(self.path, is_postgres=is_postgis)
        return self.source

    def check_schema_geonode(self, layername, glayername, ignore_case=False):
        gpkg_layer = self.get_layer_by_name(layername)
        glayer = Layer.objects.get(alternate=glayername)
        if not gpkg_layer:
            raise SourceException("Cannot find this layer in Source")
        geonode_manager = GpkgManager(get_connection(), is_postgis=True)
        glayer = geonode_manager.get_layer_by_name(glayername.split(":").pop())
        if not glayer:
            return False
        check = GpkgManager.compare_schema(gpkg_layer, glayer, ignore_case)
        return check

    @staticmethod
    def source_layer_exists(source, layername):
        layer = source.GetLayerByName(layername)
        if layer:
            return True
        return False

    @staticmethod
    def compare_schema(layer1, layer2, ignore_case=False):
        schema1 = layer1.get_full_schema()
        schema2 = layer2.get_full_schema()
        if ignore_case:
            schema1 = [(field[0].lower(), field[1], field[2])
                       for field in layer1.get_full_schema()]
            schema2 = [(field[0].lower(), field[1], field[2])
                       for field in layer2.get_full_schema()]
        schema1.sort(key=lambda field: field[0])
        schema2.sort(key=lambda field: field[0])
        deleted_fields = [field for field in schema1 if field not in schema2]
        new_fields = [field for field in schema2 if field not in schema1]
        deleted_fields.sort(key=lambda field: field[0])
        new_fields.sort(key=lambda field: field[0])
        return {
            "compatible": schema1 == schema2,
            "deleted_fields": deleted_fields,
            "new_fields": new_fields,
        }

    def layer_exists(self, layername):
        return GpkgManager.source_layer_exists(self.source, layername)

    @staticmethod
    def get_source_layers(source):
        return [
            GpkgLayer(layer, source) for layer in source
            if layer.GetName() != "layer_styles"
        ]

    def get_layers(self):
        return self.get_source_layers(self.source)

    def get_layernames(self):
        return tuple(layer.name for layer in self.get_layers())

    def get_layer_by_name(self, layername):
        if self.layer_exists(layername):
            return GpkgLayer(
                self.source.GetLayerByName(layername), self.source)
        return None

    @staticmethod
    def read_source_schema(source):
        layers = GpkgManager.get_source_layers(source)
        return tuple((layer.name,
                      layer.get_schema() + layer.geometry_fields_schema())
                     for layer in layers)

    def read_schema(self):
        return self.read_source_schema(self.source)

    @staticmethod
    def get_layers_features(layers):
        for lyr in layers:
            yield lyr.get_features()

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
                         name=None):
        source = self.open_source(connectionString, is_postgres=True)
        layer = self.source.GetLayerByName(layername)
        assert layer
        layer = GpkgLayer(layer, source)

        return layer.copy_to_source(
            source, overwrite=overwrite, temporary=temporary, name=name)

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
        postgis_source = GpkgManager.open_source(
            connectionString, is_postgres=True)
        ds = ogr.GetDriverByName('GPKG').CreateDataSource(dest_path)
        layers = GpkgManager.get_source_layers(postgis_source) \
            if not layernames \
            else [layer for layer in
                  GpkgManager.get_source_layers(postgis_source)
                  if layer and layer.name in layernames]
        for lyr in layers:
            ds.CopyLayer(lyr.gpkg_layer, lyr.name)


def get_connection():
    storename = ogc_server_settings.datastore_db['NAME']
    store = get_store(gs_catalog, storename, settings.DEFAULT_WORKSPACE)
    db = ogc_server_settings.datastore_db
    db_name = store.connection_parameters['database']
    user = db['USER']
    password = db['PASSWORD']
    host = store.connection_parameters['host']
    port = store.connection_parameters['port']
    return GpkgManager.build_connection_string(host, db_name, user, password,
                                               int(port) if port else 5432)
