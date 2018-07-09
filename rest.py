from django.conf.urls import url
from django.core.urlresolvers import reverse
from geonode.api.api import ProfileResource
from geonode.layers.models import Layer
from guardian.shortcuts import get_perms
from tastypie import fields, http
from tastypie.authentication import (ApiKeyAuthentication, BasicAuthentication,
                                     MultiAuthentication,
                                     SessionAuthentication)
from tastypie.constants import ALL, ALL_WITH_RELATIONS
from tastypie.resources import ModelResource
from tastypie.utils import trailing_slash

from cartoview.log_handler import get_logger

from .authorization import GpkgAuthorization
from .handlers import SLUGIFIER, GpkgManager, StyleManager, get_connection
from .models import GpkgUpload
from .publishers import GeonodePublisher, GeoserverPublisher

logger = get_logger(__name__)


def ensure_postgis_connection(func):
    def wrap(request, *args, **kwargs):
        this = args[0]
        conn = get_connection()
        source = GpkgManager.open_source(conn, is_postgres=True)
        if not source:
            return this.get_err_response(
                request, "Cannot Connect To Postgres Please Contact the admin",
                http.HttpApplicationError)
        return func(request, *args, **kwargs)

    return wrap


class MultipartResource(object):
    def deserialize(self, request, data, format=None):
        logger.error(request.POST)
        logger.error(request.FILES)
        if not format:
            format = request.META.get('CONTENT_TYPE', 'application/json')

        if format == 'application/x-www-form-urlencoded':
            return request.POST

        if format.startswith('multipart/form-data'):
            multipart_data = request.POST.copy()
            multipart_data.update(request.FILES)
            logger.error(request.FILES)
            return multipart_data

        return super(MultipartResource, self).deserialize(
            request, data, format)

    def post_list(self, request, **kwargs):
        if request.META.get('CONTENT_TYPE', '').startswith(
                'multipart/form-data') and not hasattr(request, '_body'):
            request._body = ''
        return super(MultipartResource, self).post_list(request, **kwargs)

    def post_detail(self, request, **kwargs):
        if request.META.get('CONTENT_TYPE', '').startswith(
                'multipart/form-data') and not hasattr(request, '_body'):
            request._body = ''
        return super(MultipartResource, self).post_detail(request, **kwargs)

    def put_detail(self, request, **kwargs):
        if request.META.get('CONTENT_TYPE', '').startswith(
                'multipart/form-data') and not hasattr(request, '_body'):
            request._body = ''
        return super(MultipartResource, self).put_detail(request, **kwargs)

    def patch_detail(self, request, **kwargs):
        if request.META.get('CONTENT_TYPE', '').startswith(
                'multipart/form-data') and not hasattr(request, '_body'):
            request._body = ''
        return super(MultipartResource, self).patch_detail(request, **kwargs)


class GpkgUploadResource(MultipartResource, ModelResource):
    package = fields.FileField(attribute="package", null=False, blank=False)
    user = fields.ForeignKey(ProfileResource, 'user', full=False, null=True)
    layers = fields.ListField(null=True, blank=True)

    def dehydrate_layers(self, bundle):
        layers = []
        for layer in bundle.obj.gpkg_manager.get_layers():
            lyr = {
                "feature_count": layer.feature_count,
                "expected_name": layer.get_new_name(),
                "name": layer.name,
                "geometry_type_name": layer.geometry_type_name,
                "geometry_type": layer.geometry_type
            }
            layers.append(lyr)
        return layers

    def hydrate_user(self, bundle):
        bundle.obj.user = bundle.request.user
        return bundle

    class Meta:
        resource_name = "geopackage_manager"
        queryset = GpkgUpload.objects.all()
        allowed_methods = ['get', 'post', 'put']
        filtering = {
            "id": ALL,
            "uploaded_at": ALL,
            "updated_at": ALL,
            "user": ALL_WITH_RELATIONS
        }
        authorization = GpkgAuthorization()
        authentication = MultiAuthentication(ApiKeyAuthentication(),
                                             BasicAuthentication(),
                                             SessionAuthentication())

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/(?P<layername>[^/]*)/publish%s$"
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('publish'),
                name="api_geopackage_publish"),
        ]

    def get_err_response(self,
                         request,
                         message,
                         response_class=http.HttpApplicationError):
        data = {
            'error_message': message,
        }
        return self.error_response(
            request, data, response_class=response_class)

    @ensure_postgis_connection
    def publish(self, request, pk, layername, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)
        upload_id = pk
        publish_name = request.GET.get('publish_name', None)
        user = request.user
        layername = str(layername)
        publish_name = str(publish_name)
        gs_layername = SLUGIFIER(layername) if not publish_name else SLUGIFIER(
            publish_name)
        gs_layername = str(gs_layername)
        try:
            upload = GpkgUpload.objects.get(pk=upload_id)
        except GpkgUpload.DoesNotExist as e:
            return self.get_err_response(request, e.message, http.HttpNotFound)
        if 'publish_from_package' in get_perms(user, upload):
            manager = upload.gpkg_manager
            package_layer = manager.get_layer_by_name(layername)
            if not package_layer:
                return self.get_err_response(
                    request,
                    "Cannot Find {} Layer in This Package".format(layername),
                    http.HttpNotFound)
            conn = get_connection()
            gs_pub = GeoserverPublisher()
            stm = StyleManager(upload.package.path)
            geonode_pub = GeonodePublisher(owner=request.user)
            tablename = manager.layer_to_postgis(
                layername, conn, overwrite=False, name=gs_layername)
            if not publish_name:
                gs_layername = package_layer.get_new_name()
            gs_pub.publish_postgis_layer(tablename, layername=gs_layername)
            try:
                layer = geonode_pub.publish(gs_layername)
                if layer:
                    gpkg_style = stm.get_style(layername)
                    if gpkg_style:
                        sld_body = stm.convert_sld_attributes(
                            gpkg_style.styleSLD)
                        name = gpkg_style.styleName
                        # TODO: handle none default styles
                        # useDefault = gpkg_style.useAsDefault
                        style = stm.upload_style(
                            name, sld_body, overwrite=True)
                        stm.set_default_layer_style(layer.alternate,
                                                    style.name)
                        layer.default_style = style
                        layer.save()
                    return self.create_response(
                        request, {
                            "layer_url":
                            request.build_absolute_uri(
                                reverse(
                                    'layer_detail',
                                    kwargs={
                                        "layername": layer.alternate,
                                    }))
                        },
                        response_class=http.HttpAccepted)
            except Exception as e:
                logger.error(e.message)
                if tablename:
                    logger.error(
                        "DELETING Table {} from source".format(tablename))
                    source = manager.open_source(conn, True)
                    source.DeleteLayer(tablename)
                if gs_layername and Layer.objects.filter(
                        alternate__icontains=gs_layername).count() == 0:
                    gs_pub.delete_layer(gs_layername)
                return self.get_err_response(request, e.message)
