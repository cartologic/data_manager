import collections


def unicode_converter(data):
    if isinstance(data, basestring):
        return str(data)
    elif isinstance(data, collections.Mapping):
        return dict(map(unicode_converter, data.iteritems()))
    elif isinstance(data, collections.Iterable):
        return type(data)(map(unicode_converter, data))
    else:
        return data