# -*- coding: utf-8 -*-
import mimetypes
import os
from distutils.util import strtobool

from django.conf.urls import url
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import StreamingHttpResponse
from geonode.api.api import ProfileResource
from geonode.layers.models import Layer
from geonode.layers.views import _resolve_layer
from guardian.shortcuts import get_objects_for_user, get_perms
from tastypie import fields, http
from tastypie.authentication import (ApiKeyAuthentication, BasicAuthentication,
                                     MultiAuthentication,
                                     SessionAuthentication)
from tastypie.constants import ALL, ALL_WITH_RELATIONS
from tastypie.resources import ModelResource
from tastypie.utils import trailing_slash

from cartoview.log_handler import get_logger

from .authorization import GpkgAuthorization
from .decorators import FORMAT_EXT
from .exceptions import GpkgLayerException
from .handlers import GpkgManager, get_connection
from .helpers import read_in_chunks
from .models import GpkgUpload, ManagerDownload
from .publishers import GeonodePublisher, GeoserverPublisher
from .style_manager import StyleManager
from .utils import SLUGIFIER

logger = get_logger(__name__)

_PERMISSION_MSG_VIEW = ('You don\'t have permissions for this action')


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


class BaseManagerResource(ModelResource):
    def get_err_response(self,
                         request,
                         message,
                         response_class=http.HttpApplicationError):
        data = {
            'error_message': message,
        }
        return self.error_response(
            request, data, response_class=response_class)


class GpkgUploadResource(MultipartResource, BaseManagerResource):
    package = fields.FileField(attribute="package", null=False, blank=False)
    user = fields.ForeignKey(ProfileResource, 'user', full=False, null=True)
    layers = fields.ListField(null=True, blank=True)

    def dehydrate_layers(self, bundle):
        layers = []
        for layer in bundle.obj.gpkg_manager.get_layers():
            details_url = bundle.request.build_absolute_uri(
                reverse(
                    'api_layer_details',
                    kwargs={
                        "resource_name": self._meta.resource_name,
                        "upload_id": bundle.obj.id,
                        "layername": layer.name,
                        "api_name": self._meta.api_name
                    }))
            publish_url = bundle.request.build_absolute_uri(
                reverse(
                    'api_geopackage_publish',
                    kwargs={
                        "resource_name": self._meta.resource_name,
                        "upload_id": bundle.obj.id,
                        "layername": layer.name,
                        "api_name": self._meta.api_name
                    }))
            compatible_layers_url = bundle.request.build_absolute_uri(
                reverse(
                    'api_compatible_layers',
                    kwargs={
                        "resource_name": self._meta.resource_name,
                        "upload_id": bundle.obj.id,
                        "layername": layer.name,
                        "api_name": self._meta.api_name
                    }))
            download_request_url = bundle.request.build_absolute_uri(
                reverse(
                    'api_layer_download_request',
                    kwargs={
                        "resource_name": self._meta.resource_name,
                        "upload_id": bundle.obj.id,
                        "layername": layer.name,
                        "api_name": self._meta.api_name
                    }))
            urls = {
                "details_url": details_url,
                "publish_url": publish_url,
                "compatible_layers_url": compatible_layers_url,
                "download_request_url": download_request_url
            }
            lyr = {"name": layer.name, "urls": urls}
            layers.append(lyr)

        return layers

    def hydrate_user(self, bundle):
        bundle.obj.user = bundle.request.user
        return bundle

    class Meta:
        resource_name = "geopackage_manager"
        queryset = GpkgUpload.objects.all()
        allowed_methods = ['get', 'post', 'put', 'delete']
        limit = 20
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
            url(r"^(?P<resource_name>%s)/(?P<upload_id>[\d]+)/(?P<layername>[^/]*)/publish%s$"
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('publish'),
                name="api_geopackage_publish"),
            url(r"^(?P<resource_name>%s)/(?P<upload_id>[\d]+)/(?P<layername>[^/]*)%s$"
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('layer_details'),
                name="api_layer_details"),
            url(r"^(?P<resource_name>%s)/(?P<upload_id>[\d]+)/(?P<layername>[^/]*)/download_request%s$"
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('layer_download_request'),
                name="api_layer_download_request"),
            url(r"^(?P<resource_name>%s)/(?P<upload_id>[\d]+)/(?P<layername>[^/]*)/compatible_layers%s$"
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_compatible_layers'),
                name="api_compatible_layers"),
            url(r"^(?P<resource_name>%s)/(?P<upload_id>[\d]+)/(?P<layername>[^/]*)/(?P<glayername>[^/]*)/reload%s$"
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('reload_layer'),
                name="api_reload"),
            url(r"^(?P<resource_name>%s)/(?P<upload_id>[\d]+)/(?P<layername>[^/]*)/(?P<glayername>[^/]*)/compare%s$"
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('compare_to_geonode_layer'),
                name="api_compare"),
        ]

    def layer_download_request(self, request, upload_id, layername, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)
        target_format = str(request.GET.get('target_format', "GPKG"))
        target_name = str(request.GET.get('target_name', "layer"))
        if target_format not in FORMAT_EXT.keys():
            return self.get_err_response(
                request, "Not Supported Format, Supported Formats: {}".format(
                    ",".join(FORMAT_EXT.keys())), http.HttpBadRequest)
        layername = str(layername)
        try:
            obj = GpkgUpload.objects.get(id=upload_id)
            if not request.user.has_perm('download_package', obj):
                return self.get_err_response(request, _PERMISSION_MSG_VIEW,
                                             http.HttpUnauthorized)
            gpkg_layer = obj.gpkg_manager.get_layer_by_name(layername)
            if not gpkg_layer:
                raise GpkgLayerException(
                    "No Layer with this name in the package")
            with transaction.atomic():
                zip_path = gpkg_layer.as_format(target_name, target_format)
                download_obj = ManagerDownload.objects.create(
                    user=request.user, file_path=zip_path)
                url = request.build_absolute_uri(
                    reverse(
                        'api_manager_download',
                        kwargs={
                            "resource_name":
                            ManagerDownloadResource.Meta.resource_name,
                            "pk":
                            download_obj.id,
                            "api_name":
                            self._meta.api_name
                        }))
                return self.create_response(request, {"download_url": url})
        except (GpkgUpload.DoesNotExist, Layer.DoesNotExist,
                GpkgLayerException), e:
            return self.get_err_response(request, e.message)

    @ensure_postgis_connection
    def layer_details(self, request, upload_id, layername, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)
        layername = str(layername)
        try:
            obj = GpkgUpload.objects.get(id=upload_id)
            if not request.user.has_perm('view_package', obj):
                return self.get_err_response(request, _PERMISSION_MSG_VIEW,
                                             http.HttpUnauthorized)
            gpkg_layer = obj.gpkg_manager.get_layer_by_name(layername)
            if not gpkg_layer:
                raise GpkgLayerException(
                    "No Layer with this name in the package")
            return self.create_response(request, gpkg_layer.as_dict(),
                                        http.HttpAccepted)
        except (GpkgUpload.DoesNotExist, Layer.DoesNotExist,
                GpkgLayerException), e:
            return self.get_err_response(request, e.message)

    @ensure_postgis_connection
    def reload_layer(self, request, upload_id, layername, glayername,
                     **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)
        layername = str(layername)
        glayername = str(glayername)
        layer = _resolve_layer(request, glayername, 'base.change_resourcebase',
                               _PERMISSION_MSG_VIEW)
        try:
            obj = GpkgUpload.objects.get(id=upload_id)
            if not request.user.has_perm('publish_from_package', obj):
                return self.get_err_response(request, _PERMISSION_MSG_VIEW,
                                             http.HttpUnauthorized)
            gpkg_layer = obj.gpkg_manager.get_layer_by_name(layername)
            if not gpkg_layer:
                raise GpkgLayerException(
                    "No Layer with this name in the package")
            if not obj.gpkg_manager.check_schema_geonode(
                    layername, str(layer.alternate)):
                raise GpkgLayerException("Invalid schema")
            geonode_manager = GpkgManager(get_connection(), is_postgis=True)
            gpkg_layer.copy_to_source(
                geonode_manager.source,
                overwrite=True,
                name=glayername.split(":").pop())
            return self.create_response(
                request, {"status": "Layer reloaded succesfully"},
                response_class=http.HttpAccepted)
        except (GpkgUpload.DoesNotExist, Layer.DoesNotExist,
                GpkgLayerException), e:
            return self.get_err_response(request, e.message)

    @ensure_postgis_connection
    def get_compatible_layers(self, request, upload_id, layername, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)
        layername = str(layername)
        permitted = get_objects_for_user(request.user,
                                         'base.change_resourcebase')
        permitted_layers = Layer.objects.filter(id__in=permitted)
        ignore_case = str(request.GET.get('ignore_case', False))
        ignore_case = strtobool(ignore_case)
        try:
            obj = GpkgUpload.objects.get(id=upload_id)
            if not request.user.has_perm('view_package', obj):
                return self.get_err_response(
                    request, "You Don't Have \
                Permission to View this Package ", http.HttpUnauthorized)
            layers = []
            for layer in permitted_layers:
                check = obj.gpkg_manager.check_schema_geonode(
                    layername, str(layer.alternate), ignore_case)
                if check.get('compatible'):
                    lyr = {
                        "name": layer.alternate,
                        "compatible": check.get('compatible'),
                        "new_fields": check.get("new_fields", []),
                        "deleted_fields": check.get("deleted_fields", []),
                        "urls": {
                            "reload_url":
                            request.build_absolute_uri(
                                reverse(
                                    'api_reload',
                                    kwargs={
                                        "resource_name":
                                        self._meta.resource_name,
                                        "upload_id": upload_id,
                                        "layername": layername,
                                        "glayername": layer.alternate,
                                        "api_name": self._meta.api_name
                                    }))
                        }
                    }
                    layers.append(lyr)
            data = {"layers": layers}
            return self.create_response(
                request, data, response_class=http.HttpAccepted)
        except (GpkgUpload.DoesNotExist, Layer.DoesNotExist,
                GpkgLayerException), e:
            return self.get_err_response(request, e.message, http.HttpNotFound)

    @ensure_postgis_connection
    def compare_to_geonode_layer(self, request, upload_id, layername,
                                 glayername, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)
        ignore_case = str(request.GET.get('ignore_case', False))
        ignore_case = strtobool(ignore_case)
        layername = str(layername)
        glayername = str(glayername)
        try:
            obj = GpkgUpload.objects.get(id=upload_id)
            if not request.user.has_perm('view_package', obj):
                return self.get_err_response(
                    request, "You Don't Have \
                Permission to View this Package ", http.HttpUnauthorized)
            check = obj.gpkg_manager.check_schema_geonode(
                layername, glayername, ignore_case)
            return self.create_response(
                request, check, response_class=http.HttpAccepted)
        except (GpkgUpload.DoesNotExist, Layer.DoesNotExist,
                GpkgLayerException), e:
            return self.get_err_response(request, e.message)

    @ensure_postgis_connection
    def publish(self, request, upload_id, layername, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)
        replace = str(request.GET.get('replace', False))
        replace = strtobool(replace)
        publish_name = request.GET.get('publish_name', None)
        user = request.user
        layername = str(layername)
        gs_layername = SLUGIFIER(layername) if not publish_name else SLUGIFIER(
            publish_name)
        gs_layername = str(gs_layername)
        if publish_name:
            publish_name = str(publish_name)
            permitted = get_objects_for_user(request.user,
                                             'base.change_resourcebase')
            permitted_layers = Layer.objects.filter(
                id__in=permitted, alternate__contains=publish_name)
            if permitted_layers.count() == 0 and replace:
                return self.get_err_response(request, _PERMISSION_MSG_VIEW)
            elif Layer.objects.filter(alternate__contains=publish_name).count(
            ) > 0 and not replace:
                return self.get_err_response(
                    request, "Layer Already exists please choose different \
                    name for this layer")
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
            if replace:
                gs_pub.delete_layer(gs_layername)
            stm = StyleManager(upload.package.path)
            geonode_pub = GeonodePublisher(owner=request.user)
            tablename = manager.layer_to_postgis(
                layername, conn, overwrite=replace, name=gs_layername)
            if not publish_name:
                gs_layername = package_layer.get_new_name()
            gs_pub.publish_postgis_layer(tablename, layername=gs_layername)
            try:
                layer = geonode_pub.publish(gs_layername)
                logger.error(layer)
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
                    if replace:
                        gs_pub.remove_cached(layer.alternate)
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
                else:
                    return self.get_err_response(
                        request, "Failed to Publish to Geonode")
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


class ManagerDownloadResource(BaseManagerResource):
    user = fields.ForeignKey(ProfileResource, 'user', full=False, null=True)
    expired = fields.BooleanField('expired', null=False)

    class Meta:
        resource_name = "manager_download"
        queryset = ManagerDownload.objects.all()
        allowed_methods = ['get']
        limit = 20
        filtering = {
            "id": ALL,
            "created_at": ALL,
            "updated_at": ALL,
            "user": ALL_WITH_RELATIONS
        }
        authentication = MultiAuthentication(ApiKeyAuthentication(),
                                             BasicAuthentication(),
                                             SessionAuthentication())

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<pk>[\d]+)/download%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('download'),
                name="api_manager_download"),
        ]

    def download(self, request, pk, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)
        try:
            obj = ManagerDownload.objects.get(id=pk)
            if obj.expired:
                raise Exception("Expired Download, Please Request a new one")
            if obj.file_path:
                f = open(obj.file_path, "rb")
                response = StreamingHttpResponse(
                    read_in_chunks(f),
                    content_type=mimetypes.guess_type(f.name)[0])
                response['Content-Disposition'] = 'attachment;filename=%s' % (
                    os.path.basename(obj.file_path))
                return response

        except Exception as e:
            return self.get_err_response(request, e.message)
