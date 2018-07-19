try:
    import ogr
    import osr
except:
    from osgeo import ogr, osr
import requests

from .utils import SLUGIFIER


class EsriSerializer(object):
    field_types_mapping = {
        "esriFieldTypeInteger": ogr.OFTInteger64,
        "esriFieldTypeSmallInteger": ogr.OFSTInt16,
        "esriFieldTypeDouble": ogr.OFTReal,
        "esriFieldTypeSingle": ogr.OFSTFloat32,
        "esriFieldTypeString": ogr.OFTString,
        "esriFieldTypeDate": ogr.OFTString,
        "esriFieldTypeBlob": ogr.OFTBinary,
        "esriFieldTypeXML": ogr.OFTBinary,
        # "esriFieldTypeGUID": "XXXX",
    }
    ignored_fields = [
        "SHAPE_Length", "SHAPE_Area", "SHAPE.LEN", "Shape.STLength()",
        "Shape.STArea()"
    ]
    geometry_types_mapping = {
        "esriGeometryPolygon": ogr.wkbPolygon,
        "esriGeometryPoint": ogr.wkbPoint,
        "esriGeometryMultipoint": ogr.wkbMultiPoint,
        "esriGeometryPolyline": ogr.wkbLineString,
        "esriGeometryLine": ogr.wkbLineString,
        "esriGeometryCircularArc": ogr.wkbCurve,
        "esriGeometryEllipticArc": ogr.wkbCircularString,
        "esriGeometryEnvelope": ogr.wkbPolygon,
        "esriGeometryRing": ogr.wkbPolygon,
        "esriGeometryPath": ogr.wkbLineString,
    }
    ogr_geometry_types_mapping = {
        "Polygon": ogr.wkbPolygon,
        "MultiPolygon": ogr.wkbMultiPolygon,
        "Point": ogr.wkbPoint,
        "Multipoint": ogr.wkbMultiPoint,
        "LineString": ogr.wkbLineString,
        "MultiLineString": ogr.wkbMultiLineString,
    }

    def __init__(self, url):
        self._url = url
        self._data = None
        self.get_data()

    def get_data(self):
        req = requests.get(self._url + "?f=json")
        self._data = req.json()

    def build_fields(self):
        data_fields = self._data['fields']
        assert data_fields
        data_fields = [
            field for field in data_fields
            if field["type"] in self.field_types_mapping.keys()
            and field["name"] not in self.ignored_fields
        ]
        field_defns = []
        for field in data_fields:
            field_type = field["type"]
            field_defn = ogr.FieldDefn(
                str(SLUGIFIER(field["name"])),
                self.field_types_mapping[field_type])
            if field_type == "esriFieldTypeString" and field.get(
                    "length", None):
                field_defn.SetWidth(field["length"])
            if field_type in "esriFieldTypeInteger":
                field_defn.SetPrecision(64)
            if field_type != "esriFieldTypeDouble":
                field_defn.SetNullable(1)
            field_defns.append(field_defn)
        return field_defns

    def get_geometry_type(self):
        return self.geometry_types_mapping[self._data["geometryType"]]

    def get_name(self):
        return SLUGIFIER(self._data["name"].lower())

    def get_projection(self):
        projection_number = None
        try:
            srs = self._data["extent"]["spatialReference"]
            if "latestWkid" in srs:
                projection_number = srs["latestWkid"]
            elif srs["wkid"] == 102100:
                projection_number = 3857
            projection_number = srs["wkid"]
        except:
            projection_number = 4326
        testSR = osr.SpatialReference()
        res = testSR.ImportFromEPSG(projection_number)
        if res != 0:
            testSR.ImportFromEPSG(4326)
        return testSR
