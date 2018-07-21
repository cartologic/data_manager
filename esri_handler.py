# -*- coding: utf-8 -*-
try:
    import ogr
    import osr
except:
    from osgeo import ogr, osr
import json
from uuid import uuid4

from esridump.dumper import EsriDumper
from geonode.people.models import Profile
from .style_manager import StyleManager
from ags2sld.handlers import Layer as AgsLayer
from cartoview.log_handler import get_logger
import os
from .exceptions import EsriException
from .handlers import GpkgManager, get_connection
from .layer_manager import GpkgLayer
from .publishers import GeonodePublisher, GeoserverPublisher
from .serializers import EsriSerializer
from .utils import SLUGIFIER, get_new_dir

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

    def _unique_name(self, name):
        if len(name) > 63:
            name = name[:63]
        if not GpkgLayer.check_geonode_layer(name):
            return str(name)
        suffix = uuid4().__str__().split('-').pop()
        if len(name) < (63 - (len(suffix) + 1)):
            name += "_" + suffix
        else:
            name = name[:((63 - len(suffix)) - 2)] + "_" + suffix

        return self._unique_name(SLUGIFIER(name))

    def get_new_name(self, name):
        name = SLUGIFIER(name.lower())
        return self._unique_name(name)

    def esri_to_postgis(self,
                        overwrite=False,
                        temporary=False,
                        launder=False,
                        name=None):
        source = None
        layer = None
        gpkg_layer = None
        es = self.get_esri_serializer()
        if not name:
            name = self.get_new_name(es.get_name())
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
            for field in es.build_fields():
                layer.CreateField(field)
            layer.StartTransaction()
            self.create_feature(layer, first_feature, gtype, srs=coord_trans)
            while True:
                next_feature = feature_iter.next()
                self.create_feature(
                    layer, next_feature, gtype, srs=coord_trans)
        except (StopIteration, EsriException), e:
            logger.error(e.message)
            if isinstance(e, EsriException):
                layer = None
        finally:
            if source and layer:
                layer.CommitTransaction()
                source.FlushCache()
                gpkg_layer = GpkgLayer(layer, source)
                source = None
                layer = None
            return gpkg_layer

    def publish(self,
                overwrite=False,
                temporary=False,
                launder=False,
                name=None):
        try:
            geonode_layer = None
            user = Profile.objects.filter(is_superuser=True).first()
            layer = self.esri_to_postgis(overwrite, temporary, launder, name)
            if not layer:
                raise Exception("failed to copy to postgis")
            gs_layername = layer.get_new_name()
            gs_pub = GeoserverPublisher()

            geonode_pub = GeonodePublisher(owner=user)
            gs_pub.publish_postgis_layer(gs_layername, layername=gs_layername)
            geonode_layer = geonode_pub.publish(gs_layername)
            if geonode_layer:
                logger.info(geonode_layer.alternate)
                agsURL, agsId = self._layer_url.rsplit('/', 1)
                tmp_dir = get_new_dir()
                ags_layer = AgsLayer(
                    agsURL + "/", int(agsId), dump_folder=tmp_dir)
                ags_layer.dump_sld_file()
                sld_path = None
                icon_paths = []
                for file in os.listdir(tmp_dir):
                    if file.endswith(".png"):
                        icon_paths.append(os.path.join(tmp_dir, file))
                    if file.endswith(".svg"):
                        icon_paths.append(os.path.join(tmp_dir, file))
                    if file.endswith(".sld"):
                        sld_path = os.path.join(tmp_dir, file)
                if sld_path:
                    sld_body = None
                    with open(sld_path, 'r') as sld_file:
                        sld_body = sld_file.read()
                    stm = StyleManager(sld_path)
                    style = stm.upload_style(
                        gs_layername, sld_body, overwrite=True)
                    stm.set_default_layer_style(geonode_layer.alternate,
                                                style.name)
                    geonode_layer.default_style = style
                    geonode_layer.save()
                if len(icon_paths) > 0:
                    for icon_path in icon_paths:
                        uploaded = gs_pub.upload_file(open(icon_path))
                        if not uploaded:
                            logger.error("Failed To Upload SLD Icon {}".format(
                                icon_path))
                gs_pub.remove_cached(geonode_layer.alternate)

        except Exception as e:
            logger.error(e.message)
        finally:
            return geonode_layer
