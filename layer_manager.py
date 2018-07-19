# -*- coding: utf-8 -*-
import os
import shutil
import time
import zipfile
from uuid import uuid4

from geonode.layers.models import Layer

from cartoview.app_manager.helpers import create_direcotry
from cartoview.log_handler import get_logger

from .constants import _downloads_dir, _temp_dir
from .decorators import FORMAT_EXT, ensure_supported_format
from .exceptions import SourceException
from .utils import SLUGIFIER

try:
    import ogr
except:
    from osgeo import ogr
logger = get_logger(__name__)


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
        layername = layername.lower()
        if Layer.objects.filter(alternate__contains=layername).count() > 0:
            return True
        return False

    @property
    def feature_count(self):
        return len(self.gpkg_layer)

    def is_geonode_layer(self, name=None):
        if not name:
            name = self.gpkg_layer.GetName().lower()
        return self.check_geonode_layer(SLUGIFIER(name))

    @property
    def geonode_layers(self):
        layername = self.gpkg_layer.GetName()
        layername = SLUGIFIER(layername)
        return Layer.objects.filter(alternate__contains=layername)

    def _unique_name(self, name):
        if len(name) > 63:
            name = name[:63]
        if not self.is_geonode_layer(name=name):
            return str(name)
        suffix = uuid4().__str__().split('-').pop()
        if len(name) < (63 - (len(suffix) + 1)):
            name += "_" + suffix
        else:
            name = name[:((63 - len(suffix)) - 2)] + "_" + suffix

        return self._unique_name(SLUGIFIER(name))

    def get_new_name(self):
        name = SLUGIFIER(self.name.lower())
        return self._unique_name(name)

    @property
    def name(self):
        return self.gpkg_layer.GetName()

    @property
    def sluged_name(self):
        return SLUGIFIER(self.gpkg_layer.GetName().lower())

    def as_dict(self):
        lyr = {
            "feature_count": self.feature_count,
            "expected_name": self.get_new_name(),
            "name": self.name,
            "geometry_type_name": self.geometry_type_name,
            "geometry_type": self.geometry_type,
            "projection": self.get_projection(),
            "schema": self.get_full_schema(),
        }
        return lyr

    def delete(self):
        self.source.DeleteLayer(self.name)

    def copy_to_source(self,
                       dest_source,
                       overwrite=True,
                       temporary=False,
                       launder=False,
                       name=None):
        options = [
            'OVERWRITE={}'.format("YES" if overwrite else 'NO'),
            'TEMPORARY={}'.format("OFF" if not temporary else "ON"),
            'LAUNDER={}'.format("YES" if launder else "NO"),
        ]
        name = self.name if not name else name
        geom_schema = self.geometry_fields_schema()
        if dest_source:
            if not overwrite and dest_source.GetLayerByName(name):
                name = self.get_new_name()
            if len(geom_schema) > 0:
                options.append('GEOMETRY_NAME={}'.format(geom_schema[0][0]))
            dest_source.CopyLayer(self.gpkg_layer, name, options)
        else:
            raise SourceException("Can't open the source")
        return name

    def prj_file(self, dest_path):
        if dest_path:
            ext = '.prj'
            if not dest_path.endswith(ext):
                dest_path += ext
            spatial_ref = self.gpkg_layer.GetSpatialRef()
            with open(dest_path, 'w') as f:
                f.write(spatial_ref.ExportToWkt())

    @staticmethod
    def _get_new_dir(base_dir=_temp_dir):
        rand_str = uuid4().__str__().replace('-', '')[:8]
        timestr = time.strftime("%Y/%m/%d/%H/%M/%S")
        target = os.path.join(base_dir, timestr, rand_str)
        create_direcotry(target)
        return target

    @staticmethod
    def _zip(src, dst):
        zip_path = "{}.zip".format(dst) if not dst.endswith('.zip') else dst
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            abs_src = os.path.abspath(src)
            for dirname, subdirs, files in os.walk(src):
                for filename in files:
                    absname = os.path.abspath(os.path.join(dirname, filename))
                    arcname = absname[len(abs_src) + 1:]
                    print 'zipping %s as %s' % (os.path.join(
                        dirname, filename), arcname)
                    zf.write(absname, arcname)
        return zip_path

    def _remove_dir(self, target_path):
        shutil.rmtree(target_path)

    @ensure_supported_format
    def as_format(self, target_name, target_format="GPKG"):
        if target_name:
            ext = FORMAT_EXT[target_format]
            if not target_name.endswith(ext):
                target_name += ext
            tmp_dir = self._get_new_dir()
            tmp_format_path = os.path.join(tmp_dir, target_name)
            ds = ogr.GetDriverByName(target_format).CreateDataSource(
                tmp_format_path)
            ds.CopyLayer(self.gpkg_layer, self.name)
            if target_format == "ESRI Shapefile":
                self.prj_file(os.path.splitext(tmp_format_path)[0])
            download_dir = self._get_new_dir(base_dir=_downloads_dir)
            zip_path = self._zip(
                tmp_dir,
                os.path.join(download_dir,
                             os.path.splitext(target_name)[0]))
            ds = None
            self._remove_dir(tmp_dir)
            return zip_path

    def get_projection(self):
        srs = self.gpkg_layer.GetSpatialRef()
        data = {
            "proj4": srs.ExportToProj4(),
            "projcs": srs.GetAttrValue('projcs'),
            "geocs": srs.GetAttrValue('geogcs')
        }
        return data

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
        return self.get_none_geom_schema() + self.geometry_fields_schema()

    def get_features(self):
        # get a feature with GetFeature(featureindex)
        # this is the one where featureindex may not start at 0
        self.gpkg_layer.ResetReading()
        # get a metadata field with GetField('fieldname'/fieldindex)
        return [{
            'fid': feature.GetFID(),
            'metadata_keys': feature.keys(),
            'metadata_dict': feature.items(),
            'geometry': feature.geometry()
        } for feature in self.gpkg_layer]
