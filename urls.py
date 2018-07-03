from django.conf.urls import url

from .views import (UploadView, compare_to_geonode_layer, deleteUpload,
                    download_layers, get_compatible_layers, publish_layer,
                    reload_layer)

urlpatterns = [
    url(r'^upload/', UploadView.as_view(),
        name="geopackage_upload"),
    url(r'^publish/(?P<upload_id>[\d]+)/(?P<layername>[^/]*)$', publish_layer,
        name="geopackage_publish"),
    url(r'^publish/(?P<upload_id>[\d]+)/(?P<layername>[^/]*)/(?P<publish_name>[^/]*)$', publish_layer,
        name="geopackage_publish_name"),
    url(r'^compare_schema/(?P<upload_id>[\d]+)/(?P<layername>[^/]*)/(?P<glayername>[^/]*)$', compare_to_geonode_layer,
        name="compare_schema"),
    url(r'^reload_layer/(?P<upload_id>[\d]+)/(?P<layername>[^/]*)/(?P<glayername>[^/]*)$', reload_layer,
        name="reload_layer"),
    url(r'^compatible_layers/(?P<upload_id>[\d]+)/(?P<layername>[^/]*)/$', get_compatible_layers,
        name="compatible_layers"),
    url(r'^delete/(?P<upload_id>[\d]+)/$', deleteUpload,
        name="geopackage_delete"),
    url(r'^download$', download_layers,
        name="geopackage_download"),
]
