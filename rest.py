from django.conf.urls import url
from geonode.api.api import ProfileResource
from tastypie import fields
from tastypie.authentication import (ApiKeyAuthentication, BasicAuthentication,
                                     MultiAuthentication,
                                     SessionAuthentication)
# from tastypie.authorization import DjangoAuthorization
from tastypie.constants import ALL, ALL_WITH_RELATIONS
from tastypie.resources import ModelResource
from tastypie.utils import trailing_slash

from .authorization import GpkgAuthorization
from .models import GpkgUpload


class MultipartResource(object):
    def deserialize(self, request, data, format=None):

        if not format:
            format = request.META.get('CONTENT_TYPE', 'application/json')

        if format == 'application/x-www-form-urlencoded':
            return request.POST

        if format.startswith('multipart/form-data'):
            multipart_data = request.POST.copy()
            multipart_data.update(request.FILES)
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

    def publish(self, request, layername, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)
        return self.create_response(request, [])
