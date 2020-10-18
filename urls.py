# -*- coding: utf-8 -*-
from django.urls import include, re_path
from tastypie.api import Api
from . import APP_NAME
from .rest import GpkgUploadResource, ManagerDownloadResource
from .views import (UploadView, compare_to_geonode_layer, deleteUpload,
                    download_layers, get_compatible_layers, publish_layer,
                    reload_layer)

api = Api(api_name='gpkg_api')
api.register(GpkgUploadResource())
api.register(ManagerDownloadResource())
urlpatterns = [
    re_path(r'^upload/', UploadView.as_view(), name="geopackage_upload"),
    re_path(r'^$', UploadView.as_view(), name="%s.index" % (APP_NAME)),
    re_path(r'^publish/(?P<upload_id>[\d]+)/(?P<layername>[^/]*)$',
        publish_layer,
        name="geopackage_publish"),
    re_path(r'^publish/(?P<upload_id>[\d]+)/(?P<layername>[^/]*)/(?P<publish_name>[^/]*)$',
        publish_layer,
        name="geopackage_publish_name"),
    re_path(r'^compare_schema/(?P<upload_id>[\d]+)/(?P<layername>[^/]*)/(?P<glayername>[^/]*)$',
        compare_to_geonode_layer,
        name="compare_schema"),
    re_path(r'^reload_layer/(?P<upload_id>[\d]+)/(?P<layername>[^/]*)/(?P<glayername>[^/]*)$',
        reload_layer,
        name="reload_layer"),
    re_path(r'^compatible_layers/(?P<upload_id>[\d]+)/(?P<layername>[^/]*)/$',
        get_compatible_layers,
        name="compatible_layers"),
    re_path(r'^delete/(?P<upload_id>[\d]+)/$',
        deleteUpload,
        name="geopackage_delete"),
    re_path(r'^download$', download_layers, name="geopackage_download"),
    re_path(r'^api/', include(api.urls)),
]
