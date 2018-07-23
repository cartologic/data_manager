# -*- coding: utf-8 -*-
import json
import sys
import uuid
from decimal import Decimal
import os
import requests
from django.conf import settings
from django.utils.translation import ugettext as _
from geonode.geoserver.helpers import (cascading_delete, get_store, gs_catalog,
                                       ogc_server_settings,
                                       set_attributes_from_geoserver)
from geonode.layers.models import Layer
from geonode.people.models import Profile
from geonode.security.views import _perms_info_json
from requests.auth import HTTPBasicAuth

from cartoview.log_handler import get_logger

from .helpers import urljoin

logger = get_logger(__name__)

DEFAULT_WORKSPACE = settings.DEFAULT_WORKSPACE
ICON_REL_PATH = "workspaces/{}/styles".format(DEFAULT_WORKSPACE)


class GeoserverPublisher(object):
    def __init__(
            self,
            geoserver_url=ogc_server_settings.LOCATION,
            workspace=DEFAULT_WORKSPACE,
            datastore=ogc_server_settings.datastore_db['NAME'],
            geoserver_user={
                'username': ogc_server_settings.credentials[0],
                'password': ogc_server_settings.credentials[1]
            }):
        self.base_url = geoserver_url
        self.workspace = workspace
        self.datastore = datastore
        self.username = geoserver_user.get('username',
                                           ogc_server_settings.credentials[0])
        self.password = geoserver_user.get('password',
                                           ogc_server_settings.credentials[1])

    @property
    def featureTypes_url(self):
        return urljoin(self.base_url, "rest/workspaces/", self.workspace,
                       "/datastores/", self.datastore, "/featuretypes")

    @property
    def gwc_url(self):
        return urljoin(self.base_url, "gwc/rest/")

    def get_gwc_layer_url(self, layername):
        return urljoin(self.gwc_url, "layers", layername)

    def publish_postgis_layer(self, tablename, layername):
        req = requests.post(
            self.featureTypes_url,
            headers={'Content-Type': "application/json"},
            auth=HTTPBasicAuth(self.username, self.password),
            json={"featureType": {
                "name": layername,
                "nativeName": tablename
            }})
        if req.status_code == 201:
            return True
        return False

    def delete_layer(self, layername):
        try:
            cascading_delete(gs_catalog, "{}:{}".format(
                self.workspace, layername))
        except Exception as e:
            logger.error(e.message)

    def upload_file(self, file, rel_path=ICON_REL_PATH):
        url = urljoin(self.base_url, "rest/", "resource", rel_path,
                      os.path.basename(file.name))
        print url
        req = requests.put(
            url,
            data=file.read(),
            headers={'Content-Type': 'application/octet-stream'},
            auth=HTTPBasicAuth(self.username, self.password))
        if req.status_code == 201:
            return True
        return False

    def remove_cached(self, typename):
        import geonode.geoserver.helpers as helpers
        try:
            logger.warning("Clearing Layer Cache")
            helpers._invalidate_geowebcache_layer(typename)
            # the following line for compatiblilty 2.8rc11 and 2.8
            try:
                helpers._stylefilterparams_geowebcache_layer(typename)
            except:
                pass
            logger.warning("Layer Cache Cleared")
        except BaseException as e:
            logger.error(e.message)


class GeonodePublisher(object):
    def __init__(self,
                 storename=ogc_server_settings.datastore_db['NAME'],
                 workspace=DEFAULT_WORKSPACE,
                 owner=Profile.objects.filter(is_superuser=True).first()):
        self.store = get_store(gs_catalog, storename, workspace)
        self.storename = storename
        self.workspace = workspace
        self.owner = owner

    def publish(self, layername):
        resource = gs_catalog.get_resource(
            layername, store=self.store, workspace=self.workspace)
        assert resource
        name = resource.name
        the_store = resource.store
        workspace = the_store.workspace
        layer = None
        try:
            logger.warning("=========> Creating the Layer in Django")
            layer, created = Layer.objects.get_or_create(
                name=name,
                workspace=workspace.name,
                defaults={
                    "store":
                    the_store.name,
                    "storeType":
                    the_store.resource_type,
                    "alternate":
                    "%s:%s" % (workspace.name.encode('utf-8'),
                               resource.name.encode('utf-8')),
                    "title": (resource.title or 'No title provided'),
                    "abstract":
                    resource.abstract
                    or unicode(_('No abstract provided')).encode('utf-8'),
                    "owner":
                    self.owner,
                    "uuid":
                    str(uuid.uuid4()),
                    "bbox_x0":
                    Decimal(resource.native_bbox[0]),
                    "bbox_x1":
                    Decimal(resource.native_bbox[1]),
                    "bbox_y0":
                    Decimal(resource.native_bbox[2]),
                    "bbox_y1":
                    Decimal(resource.native_bbox[3]),
                    "srid":
                    resource.projection
                })
            logger.warning("=========> Settting permissions")
            # sync permissions in GeoFence
            perm_spec = json.loads(_perms_info_json(layer))
            layer.set_permissions(perm_spec)
            logger.warning("=========> Settting Attributes")
            # recalculate the layer statistics
            set_attributes_from_geoserver(layer, overwrite=True)
            layer.save()
            logger.warning("=========> Fixing Metadata Links")
            # Fix metadata links if the ip has changed
            if layer.link_set.metadata().count() > 0:
                if not created and settings.SITEURL \
                        not in layer.link_set.metadata()[0].url:
                    layer.link_set.metadata().delete()
                    layer.save()
                    metadata_links = []
                    for link in layer.link_set.metadata():
                        metadata_links.append((link.mime, link.name, link.url))
                    resource.metadata_links = metadata_links
                    gs_catalog.save(resource)

        except Exception as e:
            logger.error(e.message)
            exception_type, error, traceback = sys.exc_info()
        else:
            if layer:
                layer.set_default_permissions()
            return layer
