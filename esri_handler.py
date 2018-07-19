# -*- coding: utf-8 -*-
try:
    import ogr
except:
    from osgeo import ogr
import json

from esridump.dumper import EsriDumper

from cartoview.log_handler import get_logger

from .serializers import EsriSerializer
from .utils import SLUGIFIER
from .handlers import (get_connection, GpkgManager)
logger = get_logger(__name__)


class EsriHandler(EsriDumper):
    def get_esri_serializer(self):
        s = EsriSerializer(self._layer_url)
        return s

    def create_feature(self, layer, featureDict, expected_type):
        try:
            geom_type = featureDict["geometry"]["type"]
            feature = ogr.Feature(layer.GetLayerDefn())
            f_json = json.dumps({
                "type":
                geom_type,
                "coordinates":
                featureDict["geometry"]["coordinates"]
            })
            geom = ogr.CreateGeometryFromJson(f_json)
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
                        url,
                        overwrite=True,
                        temporary=False,
                        launder=False,
                        name=None):
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
            layer = source.CreateLayer(
                str(name),
                srs=es.get_projection(),
                geom_type=gtype,
                options=options)
            assert layer
            for field in es.build_fields():
                layer.CreateField(field)
            layer.StartTransaction()
            GpkgManager.create_feature(layer, first_feature, gtype)
            while True:
                next_feature = feature_iter.next()
                GpkgManager.create_feature(layer, next_feature, gtype)
        except StopIteration:
            pass
        layer.CommitTransaction()
        source.FlushCache()
