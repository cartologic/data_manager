from django.conf.urls import patterns, url
from .views import publish_layer, UploadView
urlpatterns = patterns('',
                       url(r'^upload/$', UploadView.as_view(),
                           name="geopackage_upload"),
                       url(r'^publish/(?P<upload_id>[\d]+)/(?P<layername>[^/]*)$', publish_layer,
                           name="geopackage_publish"),
                       )
