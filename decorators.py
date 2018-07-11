FORMAT_EXT = {
    "GPKG": '.gpkg',
    "KML": '.kml',
    "GeoJSON": '.json',
    "GML": '.gml',
    "GPX": '.gpx',
    "GPSTrackMaker": ".gmt",
    "ESRI Shapefile": ".shp"
}


class FormatException(Exception):
    pass


def ensure_supported_format(func):
    def wrap(*args, **kwargs):
        format = kwargs.get('target_format', 'GPKG')
        if format in FORMAT_EXT.keys():
            return func(*args, **kwargs)
        else:
            raise FormatException("Unsupported Format")

    return wrap
