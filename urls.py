from django.conf.urls import patterns, url, include
from .views import upload, list_uploads, publish_layer
urlpatterns = patterns('',
                       url(r'^upload/$', upload, name="geopackage_upload"),
                       url(r'^uploaded/list/$', list_uploads,
                           name="geopackage_list"),
                       url(r'^publish/(?P<upload_id>[\d]+)/(?P<layername>[^/]*)$', publish_layer,
                           name="geopackage_publish"),
                       )
