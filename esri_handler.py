# -*- coding: utf-8 -*-
try:
    import ogr
    import osr
except:
    from osgeo import ogr, osr
import json

from esridump.dumper import EsriDumper

from cartoview.log_handler import get_logger

from .exceptions import EsriException
from .handlers import GpkgManager, get_connection
from .layer_manager import GpkgLayer
from .serializers import EsriSerializer
from .utils import SLUGIFIER

logger = get_logger(__name__)


class EsriHandler(EsriDumper):
    def get_esri_serializer(self):
        s = EsriSerializer(self._layer_url)
        return s

    def get_geom_coords(self, geom_dict):
        if "rings" in geom_dict:
            return geom_dict["rings"]
        elif "paths" in geom_dict:
            return geom_dict["paths"] if len(
                geom_dict["paths"]) > 1 else geom_dict["paths"][0]
        else:
            return geom_dict["coordinates"]

    def create_feature(self, layer, featureDict, expected_type, srs=None):
        try:
            geom_dict = featureDict["geometry"]
            geom_type = geom_dict["type"]
            feature = ogr.Feature(layer.GetLayerDefn())
            coords = self.get_geom_coords(geom_dict)
            f_json = json.dumps({"type": geom_type, "coordinates": coords})
            geom = ogr.CreateGeometryFromJson(f_json)
            if geom and srs:
                geom.Transform(srs)
            if geom and expected_type == geom.GetGeometryType():
                feature.SetGeometry(geom)
                for prop, val in featureDict["properties"].items():
                    name = str(SLUGIFIER(prop)).encode('utf-8')
                    value = val
                    if value and layer.GetLayerDefn().GetFieldIndex(name) != -1:
                        feature.SetField(name, value)
                layer.CreateFeature(feature)
        except Exception as e:
            logger.error(e)

    def esri_to_postgis(self,
                        overwrite=True,
                        temporary=False,
                        launder=False,
                        name=None):
        source = None
        layer = None
        es = self.get_esri_serializer()
        if not name:
            name = es.get_name()
        feature_iter = iter(self)
        try:
            first_feature = feature_iter.next()
            source = GpkgManager.open_source(
                get_connection(), is_postgres=True)
            source.FlushCache()
            options = [
                'OVERWRITE={}'.format("YES" if overwrite else 'NO'),
                'TEMPORARY={}'.format("OFF" if not temporary else "ON"),
                'LAUNDER={}'.format("YES" if launder else "NO"),
            ]
            gtype = es.get_geometry_type()
            coord_trans = None
            OSR_WGS84_REF = osr.SpatialReference()
            OSR_WGS84_REF.ImportFromEPSG(4326)
            projection = es.get_projection()
            if projection != OSR_WGS84_REF:
                coord_trans = osr.CoordinateTransformation(
                    OSR_WGS84_REF, projection)
            layer = source.CreateLayer(
                str(name), srs=projection, geom_type=gtype, options=options)
            assert layer
            for field in es.build_fields():
                layer.CreateField(field)
            layer.StartTransaction()
            self.create_feature(layer, first_feature, gtype, srs=coord_trans)
            while True:
                next_feature = feature_iter.next()
                self.create_feature(
                    layer, next_feature, gtype, srs=coord_trans)
        except (StopIteration, EsriException), e:
            if isinstance(e, EsriException):
                layer = None
        finally:
            if source and layer:
                layer.CommitTransaction()
                source.FlushCache()
                layer = GpkgLayer(layer, source)
            return layer
