# -*- coding: utf-8 -*-
import collections


def unicode_converter(data):
    if isinstance(data, str):
        return str(data)
    elif isinstance(data, collections.Mapping):
        return dict(map(unicode_converter, data.items()))
    elif isinstance(data, collections.Iterable):
        return type(data)(map(unicode_converter, data))
    else:
        return data


def urljoin(*args):
    return "/".join(map(lambda x: str(x).rstrip('/'), args))


def read_in_chunks(obj, chunk_size=2048):
    if isinstance(obj, file):
        while True:
            data = obj.read(chunk_size)
            if not data:
                break
            yield data
    else:
        for i in range(0, len(obj), chunk_size):
            yield obj[i:i + chunk_size]
