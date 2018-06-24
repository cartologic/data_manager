# -*- coding: utf-8 -*-
try:
    import ogr
except:
    from osgeo import ogr
import pipes
import subprocess
from collections import namedtuple
from geonode.layers.models import Layer
from sys import stdout
import logging

formatter = logging.Formatter(
    '[%(asctime)s] p%(process)s  { %(name)s %(pathname)s:%(lineno)d} \
                            %(levelname)s - %(message)s', '%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(stdout)
handler.setFormatter(formatter)
logger.addHandler(handler)
LayerPostgisOptions = namedtuple(
    'LayerPostgisOptions', ['skipfailures', 'overwrite', 'append', 'update'])
POSTGIS_OPTIONS = LayerPostgisOptions(True, True, False, False)


class GpkgLayer(object):
    def __init__(self, layer, source):
        self.gpkg_layer = layer
        self.name = self.gpkg_layer.GetName()
        self.layer_defn = self.gpkg_layer.GetLayerDefn()
        self.geometry_type = self.gpkg_layer.GetGeomType()
        self.source = source

    def get_schema(self):
        return [(self.layer_defn.GetFieldDefn(i).GetName(),
                 self.layer_defn.GetFieldDefn(i).GetTypeName(),
                 self.layer_defn.GetFieldDefn(i).GetType())
                for i in range(self.layer_defn.GetFieldCount())]

    @property
    def is_geonode_layer(self):
        layername = self.gpkg_layer.GetName()
        if Layer.objects.filter(typename__contains=layername).count() > 0:
            return True
        return False

    @property
    def name(self):
        return self.gpkg_layer.GetName()

    def copy_to_source(self, dest_source, overwrite=True,
                       temporary=False):
        if dest_source:
            dest_source.CopyLayer(self.gpkg_layer, self.name, [
                'OVERWRITE={}'.format("YES" if overwrite else 'NO'),
                'TEMPORARY={}'.format("OFF" if not temporary else "ON")])

    def get_projection(self):
        # self.gpkg_layer.GetSpatialRef().ExportToProj4()
        return self.gpkg_layer.GetSpatialRef().GetAttrValue('projcs')

    def geometry_fields_schema(self):
        # some layers have multiple geometric feature types
        # most of the time, it should only have one though
        return [(self.layer_defn.GetGeomFieldDefn(i).GetName(),
                 # some times the name doesn't appear
                 # but the type codes are well defined
                 ogr.GeometryTypeToName(
                     self.layer_defn.GetGeomFieldDefn(i).GetType()),
                 self.layer_defn.GetGeomFieldDefn(i).GetType()) \
                for i in range(self.layer_defn.GetGeomFieldCount())]

    def get_features(self):
        # get a feature with GetFeature(featureindex)
        # this is the one where featureindex may not start at 0
        self.gpkg_layer.ResetReading()
        # get a metadata field with GetField('fieldname'/fieldindex)
        return [{'fid': feature.GetFID(),
                 'metadata_keys': feature.keys(),
                 'metadata_dict': feature.items(),
                 'geometry': feature.geometry()}
                for feature in self.gpkg_layer]


class GpkgManager(object):
    def __init__(self, package_path):
        self.path = package_path
        self.get_source()

    @staticmethod
    def build_connection_string(DB_server, DB_Name, DB_user, DB_Pass, DB_Port=5432):
        connectionString = "host=%s port=%d dbname=%s user=%s password=%s" % (
            DB_server, DB_Port, DB_Name, DB_user, DB_Pass)
        return connectionString

    @staticmethod
    def open_source(source_path, is_postgres=False):
        full_path = "PG: "+source_path if is_postgres else source_path
        return ogr.Open(full_path)

    def get_source(self):
        self.source = self.open_source(self.path)
        return self.source

    @staticmethod
    def source_layer_exists(source, layername):
        layer = source.GetLayerByName(layername)
        if layer:
            return True
        return False

    def layer_exists(self, layername):
        return GpkgManager.source_layer_exists(self.source, layername)

    @staticmethod
    def get_source_layers(source):
        return [GpkgLayer(layer, source) for layer in source]

    def get_layers(self):
        return self.get_source_layers(self.source)

    def get_layernames(self):
        return tuple(layer.name for layer in self.get_layers())

    @staticmethod
    def read_source_schema(source):
        layers = GpkgManager.get_source_layers(source)
        return tuple((layer.name, layer.get_schema() +
                      layer.geometry_fields_schema())
                     for layer in layers)

    def read_schema(self):
        return self.read_source_schema(self.source)

    @staticmethod
    def get_layers_features(layers):
        for lyr in layers:
            yield lyr.get_features()

    def get_features(self):
        return self.get_layers_features(self.get_layers())

    def _cmd_lyr_postgis(self, gpkg_path, connectionString, layername,
                         options=POSTGIS_OPTIONS._asdict()):

        overwrite = options.get('overwrite', POSTGIS_OPTIONS.overwrite)
        skipfailures = options.get(
            'skipfailures', POSTGIS_OPTIONS.skipfailures)
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
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        out, err = p.communicate()
        return out, err

    def layer_to_postgis(self, layername, connectionString, overwrite=True,
                         temporary=False):
        source = self.open_source(connectionString, is_postgres=True)
        layer = self.source.GetLayerByName(layername)
        assert layer
        source.CopyLayer(layer, layer.GetName(), [
                         'OVERWRITE={}'.format("YES" if overwrite else 'NO'),
                         'TEMPORARY={}'.format("OFF" if not temporary else "ON")])

    def layer_to_postgis_cmd(self, layername, connectionString, options=None):
        cmd = self._cmd_lyr_postgis(
            self.path, connectionString, layername,
            options=options if options else POSTGIS_OPTIONS._asdict())
        out, err = self.execute(cmd)
        if not err:
            logger.warning("{} Added Successfully".format(layername))

    @staticmethod
    def postgis_as_gpkg(connectionString, dest_path, layernames=None):
        postgis_source = GpkgManager.open_source(
            connectionString, is_postgres=True)
        ds = ogr.GetDriverByName('GPKG').CreateDataSource(dest_path)
        layers = GpkgManager.get_source_layers(postgis_source) \
            if not layernames \
            else [layer for layer in
                  GpkgManager.get_source_layers(postgis_source)
                  if layer.name in layernames]
        for lyr in layers:
            ds.CopyLayer(lyr.gpkg_layer, lyr.name)
