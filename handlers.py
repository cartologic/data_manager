# -*- coding: utf-8 -*-
try:
    import ogr
except:
    from osgeo import ogr
import pipes
import subprocess
from collections import namedtuple
from geonode.layers.models import Layer
from contextlib import contextmanager
from .helpers import unicode_converter
from django.conf import settings
from geonode.geoserver.helpers import gs_catalog
try:
    import _sqlite3 as sqlite3
except:
    import sqlite3
from geonode.layers.models import Style
import time
from geonode.geoserver.helpers import (get_store, ogc_server_settings)
from slugify import Slugify
from cartoview.log_handler import get_logger
logger = get_logger(__name__)
LayerPostgisOptions = namedtuple(
    'LayerPostgisOptions', ['skipfailures', 'overwrite', 'append', 'update'])
POSTGIS_OPTIONS = LayerPostgisOptions(True, True, False, False)

SLUGIFIER = Slugify(separator='_')


class GpkgLayerException(Exception):
    pass


class GpkgLayer(object):
    def __init__(self, layer, source):
        self.gpkg_layer = layer
        self.layer_defn = self.gpkg_layer.GetLayerDefn()
        self.geometry_type = self.gpkg_layer.GetGeomType()
        self.geometry_type_name = ogr.GeometryTypeToName(self.geometry_type)
        self.source = source

    def get_none_geom_schema(self):
        schema = [(self.layer_defn.GetFieldDefn(i).GetName(),
                   self.layer_defn.GetFieldDefn(i).GetTypeName(),
                   self.layer_defn.GetFieldDefn(i).GetType())
                  for i in range(self.layer_defn.GetFieldCount())]
        return schema

    @staticmethod
    def check_geonode_layer(layername):
        if Layer.objects.filter(alternate__contains=layername).count() > 0:
            return True
        return False

    @property
    def feature_count(self):
        return len(self.gpkg_layer)

    @property
    def is_geonode_layer(self):
        layername = self.gpkg_layer.GetName()
        return GpkgLayer.check_geonode_layer(SLUGIFIER(layername))

    @property
    def geonode_layers(self):
        layername = self.gpkg_layer.GetName()
        layername = SLUGIFIER(layername)
        return Layer.objects.filter(alternate__contains=layername)

    def get_new_name(self):
        timestr = time.strftime("%Y%m%d_%H%M%S")
        return "{}_{}".format(SLUGIFIER(self.name), timestr)

    @property
    def name(self):
        return self.gpkg_layer.GetName()

    @property
    def sluged_name(self):
        return SLUGIFIER(self.gpkg_layer.GetName())

    def delete(self):
        self.source.DeleteLayer(self.name)

    def copy_to_source(self, dest_source, overwrite=True,
                       temporary=False, name=None):
        options = [
            'OVERWRITE={}'.format("YES" if overwrite else 'NO'),
            'TEMPORARY={}'.format("OFF" if not temporary else "ON")]
        name = self.name if not name else name
        geom_schema = self.geometry_fields_schema()
        if dest_source:
            if not overwrite and dest_source.GetLayerByName(name):
                name = self.get_new_name()
            if len(geom_schema) > 0:
                options.append('GEOMETRY_NAME={}'.format(geom_schema[0][0]))
            dest_source.CopyLayer(self.gpkg_layer, name, options)
        else:
            raise GpkgLayer("Can't open the source")
        return name

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

    def get_full_schema(self):
        return self.get_none_geom_schema(
        )+self.geometry_fields_schema()

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
    def __init__(self, package_path, is_postgis=False):
        self.path = package_path
        self.get_source(is_postgis=is_postgis)

    @staticmethod
    def build_connection_string(DB_server, DB_Name, DB_user, DB_Pass,
                                DB_Port=5432):
        connectionString = "host=%s port=%d dbname=%s user=%s password=%s" % (
            DB_server, DB_Port, DB_Name, DB_user, DB_Pass)
        return connectionString

    @staticmethod
    def open_source(source_path, is_postgres=False):
        full_path = "PG: "+source_path if is_postgres else source_path
        return ogr.Open(full_path)

    def get_source(self, is_postgis=False):
        self.source = self.open_source(self.path, is_postgres=is_postgis)
        return self.source

    @staticmethod
    def source_layer_exists(source, layername):
        layer = source.GetLayerByName(layername)
        if layer:
            return True
        return False

    @staticmethod
    def compare_schema(layer1, layer2):
        schema1 = [field[0].lower() for field in layer1.get_full_schema()]
        schema1 = GpkgLayer.sort_field_by_name(schema1)
        schema2 = [field[0].lower() for field in layer2.get_full_schema()]
        schema2 = GpkgLayer.sort_field_by_name(schema2)
        return schema1 == schema2

    def layer_exists(self, layername):
        return GpkgManager.source_layer_exists(self.source, layername)

    @staticmethod
    def get_source_layers(source):
        return [GpkgLayer(layer, source) for layer in source
                if layer.GetName() != "layer_styles"]

    def get_layers(self):
        return self.get_source_layers(self.source)

    def get_layernames(self):
        return tuple(layer.name for layer in self.get_layers())

    def get_layer_by_name(self, layername):
        if self.layer_exists(layername):
            return GpkgLayer(self.source.GetLayerByName(layername),
                             self.source)
        return None

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
        layer = GpkgLayer(layer, source)
        return layer.copy_to_source(source, overwrite=overwrite,
                                    temporary=temporary)

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


class LayerStyle(object):
    def __init__(self, *args, **kwargs):
        for key in kwargs:
            setattr(self, key, kwargs[key])

    @staticmethod
    def get_attribute_names():
        attrs = []
        for name in vars(LayerStyle):
            if name.startswith("__"):
                continue
            attr = getattr(LayerStyle, name)
            if callable(attr):
                continue
            attrs.append(name)
        return attrs

    def as_dict(self):
        return {attr: getattr(self, attr)
                for attr in self.get_attribute_names()}


class StyleManager(object):
    styles_table_name = 'layer_styles'

    def __init__(self, gpkg_path):
        self.db_path = gpkg_path

    @contextmanager
    def db_session(self, row_factory=True):
        conn = sqlite3.connect(self.db_path)
        if row_factory:
            conn.row_factory = lambda c, r: dict(
                [(col[0], r[idx]) for idx, col in enumerate(c.description)])
        yield conn
        conn.close()

    def upload_style(self, style_name, sld_body, overwrite=False):
        name = self.get_new_name(style_name)
        gs_catalog.create_style(name, sld_body, overwrite=overwrite,
                                raw=True, workspace=settings.DEFAULT_WORKSPACE)
        style = gs_catalog.get_style(
            name, workspace=settings.DEFAULT_WORKSPACE)
        style_url = style.body_href
        return Style.objects.create(
            name=name, sld_title=name, sld_body=sld_body,
            sld_url=style_url)

    def set_default_layer_style(self, layername, stylename):
        gs_layer = gs_catalog.get_layer(layername)
        gs_layer.default_style = gs_catalog.get_style(
            stylename, workspace=settings.DEFAULT_WORKSPACE)
        gs_catalog.save(gs_layer)

    def get_new_name(self, sld_name):
        sld_name = SLUGIFIER(sld_name)
        style = gs_catalog.get_style(
            sld_name, workspace=settings.DEFAULT_WORKSPACE)
        if not style:
            return sld_name
        else:
            timestr = time.strftime("%Y%m%d_%H%M%S")
            return "{}_{}".format(sld_name, timestr)

    def table_exists_decorator(failure_result=None):
        def wrapper(function):
            def wrapped(*args, **kwargs):
                this = args[0]
                if this.check_styles_table_exists():
                    return function(*args, **kwargs)
                return failure_result
            return wrapped
        return wrapper

    def check_styles_table_exists(self):
        check = 0
        with self.db_session(row_factory=False) as session:
            cursor = session.cursor()
            cursor.execute(
                """SELECT count(*) FROM sqlite_master \
                WHERE type="table" AND name=?""", (self.styles_table_name,))
            result = cursor.fetchone()
            check = result[0]
        return check

    @staticmethod
    def from_row(row):
        return LayerStyle(**unicode_converter(row))

    @table_exists_decorator(failure_result=[])
    def get_styles(self):
        with self.db_session() as session:
            cursor = session.cursor()
            cursor.execute('select * from {}'.format(self.styles_table_name))
            rows = cursor.fetchall()
            styles = [self.from_row(row) for row in rows]
            return styles

    def create_table(self):
        if not self.check_styles_table_exists():
            with self.db_session() as session:
                cursor = session.cursor()
                cursor.execute('''
                CREATE TABLE {} (
                                    `id`	INTEGER PRIMARY KEY AUTOINCREMENT,
                                    `f_table_catalog`	TEXT ( 256 ),
                                    `f_table_schema`	TEXT ( 256 ),
                                    `f_table_name`	TEXT ( 256 ),
                                    `f_geometry_column`	TEXT ( 256 ),
                                    `styleName`	TEXT ( 30 ),
                                    `styleQML`	TEXT,
                                    `styleSLD`	TEXT,
                                    `useAsDefault`	BOOLEAN,
                                    `description`	TEXT,
                                    `owner`	TEXT ( 30 ),
                                    `ui`	TEXT ( 30 ),
                                    `update_time`	DATETIME DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                                );'''.format(self.styles_table_name))
                session.commit()

    @table_exists_decorator(failure_result=None)
    def get_style(self, layername):
        with self.db_session() as session:
            cursor = session.cursor()
            cursor.execute(
                'SELECT * FROM {} WHERE f_table_name=?'.format(
                    self.styles_table_name),
                (layername,))
            rows = cursor.fetchone()
            return self.from_row(rows) if len(rows) > 0 else None

    @table_exists_decorator(failure_result=None)
    def add_style(self, layername, geom_field, stylename, sld_body,
                  default=False):
        with self.db_session() as session:
            cursor = session.cursor()
            cursor.execute(
                'INSERT INTO {} (f_table_name,f_geometry_column,styleName,styleSLD,useAsDefault) VALUES (?,?,?,?,?);'.format(
                    self.styles_table_name),
                (layername, geom_field, stylename,
                 sld_body, default))
            session.commit()
            return cursor.lastrowid
    # TODO: add_styles with executemany


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
