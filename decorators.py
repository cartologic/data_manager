# -*- coding: utf-8 -*-
from datetime import datetime
from functools import wraps

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


def time_it(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        start = datetime.now()
        result = function(request, *args, **kwargs)
        end = datetime.now()
        print("{} took ------>{} seconds".format(
            function.func.__name__, (end - start).total_seconds()))
        print("{} took ------>{} milliseconds".format(
            function.func.__name__, (end - start).total_seconds() * 1000))
        return result

    return wrap
