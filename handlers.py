# -*- coding: utf-8 -*-
from osgeo import ogr
import pprint
import pipes
import subprocess

DEFAULT_OPTIONS = {
    'skipfailures': True,
    'overwrite': True,
    'append': False,
    'update': False
}


class GpkgLayer(object):
    def __init__(self, layer):
        self.gpkg_layer = layer
        self.name = self.gpkg_layer.GetName()
        self.layer_defn = self.gpkg_layer.GetLayerDefn()
        self.geometry_type = self.gpkg_layer.GetGeomType()

    def get_schema(self):
        return [(self.layer_defn.GetFieldDefn(i).GetName(),
                 self.layer_defn.GetFieldDefn(i).GetTypeName(),
                 self.layer_defn.GetFieldDefn(i).GetType())
                for i in range(self.layer_defn.GetFieldCount())]

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
    def build_connection_string(DB_server, DB_Name, DB_user, DB_Pass):
        connectionString = "host=%s dbname=%s user=%s password=%s" % (
            DB_server, DB_Name, DB_user, DB_Pass)
        return connectionString

    def open_source(self, source_path, is_postgres=False):
        full_path = "PG: "+source_path if is_postgres else source_path
        return ogr.Open(full_path)

    def get_source(self):
        self.source = self.open_source(self.path)
        return self.source

    def get_source_layers(self, source):
        return [GpkgLayer(layer) for layer in source]

    def get_layers(self):
        return self.get_source_layers(self.source)

    def get_layernames(self):
        return tuple(layer.name for layer in self.get_layers())

    def read_source_schema(self, source):
        layers = self.get_source_layers(source)
        return tuple((layer.name, layer.get_schema() +
                      layer.geometry_fields_schema())
                     for layer in layers)

    def read_schema(self):
        return self.read_source_schema(self.source)

    def get_layers_features(self, layers):
        for lyr in layers:
            yield lyr.get_features()

    def get_features(self):
        return self.get_layers_features(self.get_layers())

    def cmd_lyr_postgis(self, gpkg_path, connectionString, layername,
                        options=DEFAULT_OPTIONS):
        overwrite = options.get('overwrite', DEFAULT_OPTIONS.get('overwrite'))
        skipfailures = options.get(
            'skipfailures', DEFAULT_OPTIONS.get('skipfailures'))
        append_layer = options.get('append', DEFAULT_OPTIONS.get('append'))
        update_layer = options.get('update', DEFAULT_OPTIONS.get('update'))
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
        print out
        return out, err

    def layer_to_postgis(self, layername, connectionString):
        options = DEFAULT_OPTIONS.copy()
        options.update({'append': True})
        cmd = self.cmd_lyr_postgis(
            self.path, connectionString, layername, options=options)
        out, err = self.execute(cmd)
        if not err:
            print "{} Added Successfully".format(layername)

    # def as_gpkg(self):
    #     ds = ogr.GetDriverByName('GPKG').CreateDataSource(
    #         '/Users/hishamkaram/Projects-Active/cartoview_project/gdal_sample.gpkg')
    #     layers = self.read_layers()
    #     for lyr in layers:
    #         ds.CopyLayer(lyr, lyr.GetName())
    #         # pprint.pprint(lyr.GetName())
    #         # dest_layer = ds.CreateLayer(lyr.GetName(),
    #         #                             srs=lyr.GetSpatialRef(),
    #         #                             geom_type=lyr.GetLayerDefn().GetGeomType())
    #         # feature = lyr.GetFeature(0)
    #         # for i in range(feature.GetFieldCount()):
    #         #     dest_layer.CreateField(feature.GetFieldDefnRef(i))
    #         # lyr.ResetReading()
    #         # for feature in lyr:
    #         #     pprint.pprint(feature.GetFID())
    #         #     dest_layer.CreateFeature(feature)


single = GpkgManager('/Users/hishamkaram/Projects-Active/one_layer.gpkg')
multi = GpkgManager(
    '/Users/hishamkaram/Projects-Active/three_layers_scemd.gpkg')
# print("Single===============================\n")
# pprint.pprint(single.read_source_schema())
# print("Multiple===============================\n")
# pprint.pprint(multi.read_source_schema())
print("===============================Package Layers==========================")
pprint.pprint(multi.get_layernames())
print("===============================END==========================")
# pprint.pprint(multi.get_features().next())
# x = PostgisHandler('127.0.0.1', 'cartoview_datastore', 'hishamkaram', 'clogic')
# pprint.pprint(x.read_layers())
# x.as_gpkg()
# /Library/Frameworks/GDAL.framework/Versions/2.1/Programs/ogr2ogr -overwrite -f "PostgreSQL" PG:"host=127.0.0.1 user=hishamkaram password=clogic dbname=cartoview_datastore"  ../three_layers_scemd.gpkg  -skipfailures -clipsrclayer three_layers_scemd
# /Library/Frameworks/GDAL.framework/Versions/1.11/Python/2.7/site-packages/osgeo
print("===============================Starting upload layer to postgis==========================")
multi.layer_to_postgis("scemd_example_data quakes_1776_2008",
                       GpkgManager.build_connection_string('127.0.0.1', 'cartoview_datastore', 'hishamkaram', 'clogic'))
print("===============================END==========================")
