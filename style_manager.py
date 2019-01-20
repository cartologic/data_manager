# -*- coding: utf-8 -*-
import time
from contextlib import contextmanager
from io import BytesIO

import lxml
from django.conf import settings
from geonode.geoserver.helpers import gs_catalog
from geonode.layers.models import Style

from .helpers import unicode_converter
from .utils import SLUGIFIER

try:
    import _sqlite3 as sqlite3
except ImportError:
    import sqlite3


class LayerStyle(object):
    def __init__(self, *args, **kwargs):
        for key in kwargs:
            setattr(self, key, kwargs[key])

    @staticmethod
    def get_attribute_names():
        attrs = []
        for name in vars(LayerStyle):
            if name.startswith("__"):
                continue
            attr = getattr(LayerStyle, name)
            if callable(attr):
                continue
            attrs.append(name)
        return attrs

    def as_dict(self):
        return {
            attr: getattr(self, attr)
            for attr in self.get_attribute_names()
        }


class StyleManager(object):
    styles_table_name = 'layer_styles'

    def __init__(self, gpkg_path):
        self.db_path = gpkg_path

    @contextmanager
    def db_session(self, row_factory=True):
        conn = sqlite3.connect(self.db_path)
        if row_factory:
            conn.row_factory = lambda c, r: dict(
                [(col[0], r[idx]) for idx, col in enumerate(c.description)])
        yield conn
        conn.close()

    def upload_style(self, style_name, sld_body, overwrite=False):
        name = self.get_new_name(style_name)
        gs_catalog.create_style(
            name,
            sld_body,
            overwrite=overwrite,
            raw=True,
            workspace=settings.DEFAULT_WORKSPACE)
        style = gs_catalog.get_style(
            name, workspace=settings.DEFAULT_WORKSPACE)
        style_url = style.body_href
        gstyle, created = Style.objects.get_or_create(
            name=name,
            sld_title=name,
            workspace=settings.DEFAULT_WORKSPACE,
            sld_body=sld_body,
            sld_url=style_url)
        return gstyle

    def set_default_layer_style(self, layername, stylename):
        gs_layer = gs_catalog.get_layer(layername)
        gs_layer.default_style = gs_catalog.get_style(
            stylename, workspace=settings.DEFAULT_WORKSPACE)
        gs_catalog.save(gs_layer)

    def get_new_name(self, sld_name):
        sld_name = SLUGIFIER(sld_name)
        style = gs_catalog.get_style(
            sld_name, workspace=settings.DEFAULT_WORKSPACE)
        if not style:
            return sld_name
        else:
            timestr = time.strftime("%Y%m%d_%H%M%S")
            return "{}_{}".format(sld_name, timestr)

    def table_exists_decorator(failure_result=None):
        def wrapper(function):
            def wrapped(*args, **kwargs):
                this = args[0]
                if this.check_styles_table_exists():
                    return function(*args, **kwargs)
                return failure_result

            return wrapped

        return wrapper

    def check_styles_table_exists(self):
        check = 0
        with self.db_session(row_factory=False) as session:
            cursor = session.cursor()
            cursor.execute(
                """SELECT count(*) FROM sqlite_master \
                WHERE type="table" AND name=?""", (self.styles_table_name, ))
            result = cursor.fetchone()
            check = result[0]
        return check

    @staticmethod
    def from_row(row):
        return LayerStyle(**unicode_converter(row))

    @table_exists_decorator(failure_result=[])
    def get_styles(self):
        with self.db_session() as session:
            cursor = session.cursor()
            cursor.execute('select * from {}'.format(self.styles_table_name))
            rows = cursor.fetchall()
            styles = [self.from_row(row) for row in rows]
            return styles

    def create_table(self):
        if not self.check_styles_table_exists():
            with self.db_session() as session:
                cursor = session.cursor()
                cursor.execute('''
                CREATE TABLE {} (
                                    `id`	INTEGER PRIMARY KEY AUTOINCREMENT,
                                    `f_table_catalog`	TEXT ( 256 ),
                                    `f_table_schema`	TEXT ( 256 ),
                                    `f_table_name`	TEXT ( 256 ),
                                    `f_geometry_column`	TEXT ( 256 ),
                                    `styleName`	TEXT ( 30 ),
                                    `styleQML`	TEXT,
                                    `styleSLD`	TEXT,
                                    `useAsDefault`	BOOLEAN,
                                    `description`	TEXT,
                                    `owner`	TEXT ( 30 ),
                                    `ui`	TEXT ( 30 ),
                                    `update_time`	DATETIME DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                                );'''.format(self.styles_table_name))
                session.commit()

    @table_exists_decorator(failure_result=None)
    def get_style(self, layername):
        with self.db_session() as session:
            cursor = session.cursor()
            cursor.execute(
                'SELECT * FROM {} WHERE f_table_name=?'.format(
                    self.styles_table_name), (layername, ))
            rows = cursor.fetchone()
            if rows and len(rows):
                return self.from_row(rows)
            else:
                return None

    def convert_sld_attributes(self, sld_body):
        contents = BytesIO(str(sld_body))
        tree = lxml.etree.parse(contents)
        root = tree.getroot()
        nsmap = {k: v for k, v in root.nsmap.iteritems() if k}
        properties = tree.xpath('.//ogc:PropertyName', namespaces=nsmap)
        for prop in properties:
            value = str(prop.text).lower()
            prop.text = value
        return lxml.etree.tostring(tree)

    @table_exists_decorator(failure_result=None)
    def add_style(self,
                  layername,
                  geom_field,
                  stylename,
                  sld_body,
                  default=False):
        # sld_body = self.convert_sld_attributes(sld_body)
        with self.db_session() as session:
            cursor = session.cursor()
            cursor.execute(
                'INSERT INTO {} (f_table_name,f_geometry_column,styleName,styleSLD,useAsDefault) VALUES (?,?,?,?,?);'.
                format(self.styles_table_name),
                (layername, geom_field, stylename, sld_body, default))
            session.commit()
            return cursor.lastrowid

    # TODO: add_styles with executemany
